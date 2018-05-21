import copy
import logging
import os

import six
from django.utils import timezone
from lxml import etree, isoschematron
from scandir import walk

from ESSArch_Core.essxml.util import find_files, find_pointers, validate_against_schema
from ESSArch_Core.exceptions import ValidationError
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.fixity.models import Validation
from ESSArch_Core.fixity.validation.backends.base import BaseValidator

logger = logging.getLogger('essarch.fixity.validation.xml')


class DiffCheckValidator(BaseValidator):
    """
    Validates the file against a given XML to see if is an entirely new file or
    if it has been changed or renamed/moved.

    The post validation checks if there are files that has been deleted after
    the XML was generated.
    """

    file_validator = False

    def __init__(self, *args, **kwargs):
        super(DiffCheckValidator, self).__init__(*args, **kwargs)

        if not self.context:
            raise ValueError('A context (xml) is required')

        self.rootdir = self.options.get('rootdir')
        self.default_algorithm = self.options.get('default_algorithm', 'SHA-256')

        self.initial_present     = {}  # Map checksum -> fname
        self.initial_deleted     = {}  # Map checksum -> fname
        self.sizes               = {}  # Map fname -> size
        self.checksums           = {}  # Map fname -> checksum
        self.checksum_algorithms = {}  # Map fname -> checksum algorithm

        self.logical_files = find_files(self.context, rootdir=self.rootdir)
        self._get_files()
        for logical in self.logical_files:
            if self.rootdir is not None:
                logical_path = os.path.join(self.rootdir, logical.path)
            else:
                logical_path = logical.path

            try:
                self.initial_deleted[logical.checksum].append(logical_path)
            except KeyError:
                self.initial_deleted[logical.checksum] = [logical_path]
            try:
                self.initial_present[logical.checksum].append(logical_path)
            except KeyError:
                self.initial_present[logical.checksum] = [logical_path]
            self.checksums[logical_path] = logical.checksum
            self.checksum_algorithms[logical_path] = logical.checksum_type
            self.sizes[logical_path] = logical.size

    def _reset_dicts(self):
        self.present = copy.deepcopy(self.initial_present)
        self.deleted = copy.deepcopy(self.initial_deleted)

    def _reset_counters(self):
        self.confirmed = 0
        self.added = 0
        self.changed = 0
        self.renamed = 0

    def _get_files(self):
        self.logical_files = find_files(self.context, rootdir=self.rootdir)

    def _create_obj(self, filename, passed, msg):
        return Validation(
            filename=filename,
            time_started=timezone.now(),
            time_done=timezone.now(),
            validator=self.__class__.__name__,
            required=self.required,
            information_package=self.ip,
            responsible=self.responsible,
            message=msg,
            passed=passed,
            specification={
                'context': self.context,
                'options': self.options,
            }
        )

    def _pop_checksum_dict(self, d, checksum, filepath):
        l = d[checksum]
        l.remove(filepath)

        if not len(l):
            d.pop(checksum)

    def _get_filepath(self, input_file):
        return input_file

    def _get_checksum(self, input_file):
        algorithm = self.checksum_algorithms.get(input_file, self.default_algorithm)
        return calculate_checksum(input_file, algorithm=algorithm)

    def _get_size(self, input_file):
        return os.path.getsize(input_file)

    def _validate(self, filepath):
        newhash = self._get_checksum(filepath)
        newsize = self._get_size(filepath)
        filepath = self._get_filepath(filepath)
        relpath = os.path.relpath(filepath, self.rootdir)

        try:
            self._pop_checksum_dict(self.deleted, newhash, filepath)
        except (KeyError, ValueError):
            pass

        if newhash in self.present:
            try:
                self._pop_checksum_dict(self.present, newhash, filepath)
            except ValueError:
                self.present[newhash].append(filepath)
                return
        else:
            self.present[newhash] = [filepath]

        if filepath not in self.checksums:
            return

        oldhash = self.checksums[filepath]
        if oldhash != newhash:
            self.deleted.pop(oldhash, None)
            self.changed += 1
            msg = '{f} checksum has been changed: {old} != {new}'.format(f=relpath, old=oldhash, new=newhash)
            self._pop_checksum_dict(self.present, oldhash, filepath)
            self._pop_checksum_dict(self.present, newhash, filepath)
            return self._create_obj(filepath, False, msg)

        oldsize = self.sizes[filepath]
        if oldsize is not None and newsize is not None and oldsize != newsize:
            self.deleted.pop(oldhash, None)
            self.changed += 1
            msg = '{f} size has been changed: {old} != {new}'.format(f=relpath, old=oldsize, new=newsize)
            return self._create_obj(filepath, False, msg)

        self.confirmed += 1
        msg = '{f} confirmed in xml'.format(f=relpath)
        return self._create_obj(filepath, True, msg)

    def _validate_deleted_files(self, objs):
        delete_count = 0
        for deleted_hash, deleted_hash_files in six.iteritems(self.deleted):
            present_hash_files = self.present.get(deleted_hash, [])

            for f in present_hash_files[:]:
                if f not in deleted_hash_files:
                    try:
                        old = deleted_hash_files.pop()
                        self.renamed += 1
                        msg = '{old} has been renamed to {new}'.format(old=old, new=f)
                        objs.append(self._create_obj(old, False, msg))
                        present_hash_files.remove(old)
                        present_hash_files.remove(f)
                    except IndexError:
                        pass

            for f in deleted_hash_files:
                msg = '{file} has been deleted'.format(file=f)
                objs.append(self._create_obj(f, False, msg))
                delete_count += 1
                present_hash_files.remove(f)

            if not len(present_hash_files):
                self.present.pop(deleted_hash, None)

        return delete_count

    def _validate_present_files(self, objs):
        for present_hash, present_hash_files in six.iteritems(self.present):
            for f in present_hash_files:
                self.added += 1
                msg = '{f} is missing from {xml}'.format(f=f, xml=self.context)
                objs.append(self._create_obj(f, False, msg))

    def validate(self, path):
        xmlfile = self.context
        objs = []
        self._reset_dicts()
        self._reset_counters()
        logger.debug('Validating {path} against {xml}'.format(path=path, xml=xmlfile))

        if os.path.isdir(path):
            for root, dirs, files in walk(path):
                for f in files:
                    filepath = os.path.join(root, f)
                    if filepath in self.exclude or filepath == xmlfile:
                        continue
                    objs.append(self._validate(filepath))
        else:
            objs.append(self._validate(path))

        delete_count = self._validate_deleted_files(objs)
        self._validate_present_files(objs)

        objs = [o for o in objs if o is not None]
        Validation.objects.bulk_create(objs, batch_size=100)

        if delete_count + self.added + self.changed + self.renamed > 0:
            msg = 'Diff-check validation of {path} against {xml} failed: {cfmd} confirmed, {a} added, {c} changed, {r} renamed, {d} deleted'.format(
                path=path, xml=self.context, cfmd=self.confirmed, a=self.added, c=self.changed, r=self.renamed,
                d=delete_count)
            logger.warn(msg)
            raise ValidationError(msg)

        logger.info("Successful diff-check validation of {path} against {xml}".format(path=path, xml=self.context))


class XMLComparisonValidator(DiffCheckValidator):
    def _get_files(self):
        skip_files = [p.path for p in find_pointers(self.context)]
        self.logical_files = find_files(self.context, rootdir=self.rootdir, skip_files=skip_files)

    def _get_filepath(self, input_file):
        return os.path.join(self.rootdir, input_file.path)

    def _get_checksum(self, input_file):
        return input_file.checksum

    def _get_size(self, input_file):
        return input_file.size

    def validate(self, path):
        xmlfile = self.context
        objs = []
        self._reset_dicts()
        self._reset_counters()
        logger.debug('Validating {path} against {xml}'.format(path=path, xml=xmlfile))
        checksum_in_context_file = self.checksums.get(path)

        if checksum_in_context_file:
            try:
                self._pop_checksum_dict(self.deleted, checksum_in_context_file, path)
                self._pop_checksum_dict(self.present, checksum_in_context_file, path)
            except (KeyError, ValueError):
                pass

        skip_files = [os.path.relpath(xmlfile, self.rootdir)]
        skip_files.extend([p.path for p in find_pointers(path)])
        for f in find_files(path, rootdir=self.rootdir, skip_files=skip_files):
            if f in self.exclude:
                continue
            objs.append(self._validate(f))

        delete_count = self._validate_deleted_files(objs)
        self._validate_present_files(objs)

        if checksum_in_context_file:
            try:
                self.deleted[checksum_in_context_file].append(path)
            except KeyError:
                self.deleted[checksum_in_context_file] = [path]

            try:
                self.present[checksum_in_context_file].append(path)
            except KeyError:
                self.present[checksum_in_context_file] = [path]

        objs = [o for o in objs if o is not None]
        Validation.objects.bulk_create(objs, batch_size=100)

        if delete_count + self.added + self.changed + self.renamed > 0:
            msg = 'Comparision of {path} against {xml} failed: {cfmd} confirmed, {a} added, {c} changed, {r} renamed, {d} deleted'.format(
                path=path, xml=self.context, cfmd=self.confirmed, a=self.added, c=self.changed, r=self.renamed,
                d=delete_count)
            logger.warn(msg)
            raise ValidationError(msg)

        logger.info("Successful comparison of {path} against {xml}".format(path=path, xml=self.context))


class XMLSchemaValidator(BaseValidator):
    def validate(self, filepath):
        if self.context:
            logger.debug('Validating schema of {xml} against {schema}'.format(xml=filepath, schema=self.context))
        else:
            logger.debug('Validating schema of {xml}'.format(xml=filepath))

        rootdir = self.options.get('rootdir')
        try:
            validate_against_schema(filepath, self.context, rootdir)
        except Exception as e:
            logger.warn('Schema validation of {xml} failed, {msg}'.format(xml=filepath, msg=e.message))
            raise

        logger.info("Successful schema validation of {xml}".format(xml=filepath))

class XMLSchematronValidator(BaseValidator):
    def validate(self, filepath):
        logger.debug('Validating {xml} against {schema}'.format(xml=filepath, schema=self.context))
        try:
            sct_doc = etree.parse(self.context)
            schematron = etree.Schematron(sct_doc)
            schematron.assertValid(etree.parse(filepath))
        except etree.DocumentInvalid as e:
            logger.warn('Schematron validation of {xml} against {schema} failed, {msg}'.format(xml=filepath, schema=self.context, msg=e.message))
            raise

        logger.info("Successful schematron validation of {xml} against {schema}".format(xml=filepath, schema=self.context))

class XMLISOSchematronValidator(BaseValidator):
    def validate(self, filepath):
        logger.debug('Validating {xml} against {schema}'.format(xml=filepath, schema=self.context))
        try:
            sct_doc = etree.parse(self.context)
            schematron = isoschematron.Schematron(sct_doc)
            schematron.assertValid(etree.parse(filepath))
        except etree.DocumentInvalid as e:
            logger.warn('ISO-Schematron validation of {xml} against {schema} failed, {msg}'.format(xml=filepath, schema=self.context, msg=e.message))
            raise

        logger.info("Successful iso-schematron validation of {xml} against {schema}".format(xml=filepath, schema=self.context))
