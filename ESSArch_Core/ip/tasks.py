import os
import shutil
import tarfile
import zipfile

from scandir import walk

from ESSArch_Core.WorkflowEngine.dbtask import DBTask
from ESSArch_Core.WorkflowEngine.models import ProcessTask
from ESSArch_Core.configuration.models import Path
from ESSArch_Core.essxml.Generator.xmlGenerator import XMLGenerator
from ESSArch_Core.fixity.checksum import calculate_checksum
from ESSArch_Core.ip.models import InformationPackage, MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT
from ESSArch_Core.profiles.utils import fill_specification_data
from ESSArch_Core.util import (creation_date, find_destination, get_event_spec,
                               get_premis_ip_object_element_spec,
                               timestamp_to_datetime)


class GenerateContentMets(DBTask):
    event_type = 50600
    
    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        sa = ip.submission_agreement
        profile_type = ip.get_package_type_display().lower()
        profile_rel = ip.get_profile_rel(profile_type)
        profile_data = ip.get_profile_data(profile_type)
        structure = profile_rel.profile.structure
        mets_dir, mets_name = find_destination("mets_file", structure)
        mets_path = os.path.join(ip.object_path, mets_dir, mets_name)
        files_to_create = {
            mets_path: {
                'spec': profile_rel.profile.specification,
                'data': fill_specification_data(profile_data, ip=ip, sa=sa)
            }
        }
        algorithm = ip.get_checksum_algorithm()

        generator = XMLGenerator(files_to_create)
        generator.generate(folderToParse=ip.object_path, algorithm=algorithm)

        ip.content_mets_path = mets_path
        ip.content_mets_create_date = timestamp_to_datetime(creation_date(mets_path)).isoformat()
        ip.content_mets_size = os.path.getsize(mets_path)
        ip.content_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
        ip.content_mets_digest = calculate_checksum(mets_path, algorithm=algorithm)
        ip.save()

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class GeneratePackageMets(DBTask):
    event_type = 50600

    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        sa = ip.submission_agreement
        if ip.package_type == InformationPackage.SIP:
            profile_type = 'submit_description'
        elif ip.package_type == InformationPackage.AIP:
            profile_type = 'aip_description'
        else:
            raise ValueError('Cannot create package mets for IP of type {package_type}'.format(ip.package_type))
        profile_rel = ip.get_profile_rel(profile_type)
        profile_data = ip.get_profile_data(profile_type)
        xmlpath = os.path.splitext(ip.object_path)[0] + '.xml'
        data = fill_specification_data(profile_data, ip=ip, sa=sa)
        data["_IP_CREATEDATE"] = timestamp_to_datetime(creation_date(ip.object_path)).isoformat()
        files_to_create = {
            xmlpath: {
                'spec': profile_rel.profile.specification,
                'data': data
            }
        }
        algorithm = ip.get_checksum_algorithm()

        generator = XMLGenerator(files_to_create)
        generator.generate(folderToParse=ip.object_path, algorithm=algorithm)

        ip.package_mets_path = xmlpath
        ip.package_mets_create_date = timestamp_to_datetime(creation_date(xmlpath)).isoformat()
        ip.package_mets_size = os.path.getsize(xmlpath)
        ip.package_mets_digest_algorithm = MESSAGE_DIGEST_ALGORITHM_CHOICES_DICT[algorithm.upper()]
        ip.package_mets_digest = calculate_checksum(xmlpath, algorithm=algorithm)
        ip.save()

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class GeneratePremis(DBTask):
    event_type = 50600

    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        sa = ip.submission_agreement
        premis_profile_rel = ip.get_profile_rel('preservation_metadata')
        premis_profile_data = ip.get_profile_data('preservation_metadata')
        sip_profile_rel = ip.get_profile_rel('sip')
        structure = sip_profile_rel.profile.structure
        premis_dir, premis_name = find_destination("preservation_description_file", structure)
        premis_path = os.path.join(ip.object_path, premis_dir, premis_name)
        files_to_create = {
            premis_path: {
                'spec': premis_profile_rel.profile.specification,
                'data': fill_specification_data(premis_profile_data, ip=ip, sa=sa)
            }
        }
        algorithm = ip.get_checksum_algorithm()
        generator = XMLGenerator(files_to_create)
        generator.generate(folderToParse=ip.object_path, algorithm=algorithm)

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class GenerateEventsXML(DBTask):
    event_type = 50600

    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        sa = ip.submission_agreement
        xml_path = os.path.join(ip.object_path, 'ipevents.xml')
        files_to_create = {
            xml_path: {
                'spec': get_event_spec(),
                'data': fill_specification_data(ip=ip, sa=sa)
            }
        }
        algorithm = ip.get_checksum_algorithm()
        generator = XMLGenerator(files_to_create)
        generator.generate(algorithm=algorithm)

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class DownloadSchemas(DBTask):
    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        ip_profile_type = ip.get_package_type_display().lower()
        ip_profile = ip.get_profile_rel(ip_profile_type).profile
        structure = ip_profile.structure
        rootdir = ip.object_path

        specifications = [ip_profile.specification, get_event_spec()]
        premis_profile_rel = ip.get_profile_rel('preservation_metadata')
        if premis_profile_rel is not None:
            specifications.append(premis_profile_rel.profile.specification)

        for spec in specifications:
            schema_preserve_loc = spec.get('-schemaPreservationLocation', 'xsd_files')
            if schema_preserve_loc and structure:
                reldir, _ = find_destination(schema_preserve_loc, structure)
                dirname = os.path.join(rootdir, reldir)
            else:
                dirname = rootdir
            for schema in spec.get('-schemasToPreserve', []):
                dst = os.path.join(dirname, os.path.basename(schema))

                t = ProcessTask.objects.create(
                    name="ESSArch_Core.tasks.DownloadFile",
                    params={'src': schema, 'dst': dst},
                    processstep_id=self.step,
                    processstep_pos=self.step_pos,
                    responsible_id=self.responsible,
                    information_package_id=self.ip,
                )

                t.run().get()

    def undo(self):
        pass

    def event_outcome_success(self):
        pass


class AddPremisIPObjectElementToEventsFile(DBTask):
    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        info = {
            'FIDType': "UUID",
            'FID': ip.object_identifier_value,
            'FFormatName': ip.get_container_format().upper(),
            'FLocationType': 'URI',
            'FName': ip.object_path,
        }
        spec = get_premis_ip_object_element_spec()
        info = fill_specification_data(info, ip=ip)
        xmlfile = os.path.join(ip.object_path, 'ipevents.xml')

        generator = XMLGenerator(filepath=xmlfile)
        target = generator.find_element('premis')
        generator.insert_from_specification(target, spec, data=info, index=0)
        generator.write(xmlfile)
        
    def undo(self):
        pass

    def event_outcome_success(self):
        pass
    
    
class CreateContainer(DBTask):
    def run(self):
        ip = InformationPackage.objects.get(pk=self.ip)
        container_format = ip.get_container_format().lower()
        tpp = ip.get_profile_rel('transfer_project').profile
        compress = tpp.specification_data.get('container_format_compression', False)

        src = ip.object_path
        dst_dir = Path.objects.cached('entity', 'path_preingest_reception', 'value')
        dst_filename = ip.object_identifier_value + '.' + container_format
        dst = os.path.join(dst_dir, dst_filename)

        if container_format == 'zip':
            self.event_type = 50410
            compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
            with zipfile.ZipFile(dst, 'w', compression) as new_zip:
                for root, dirs, files in walk(src):
                    for d in dirs:
                        filepath = os.path.join(root, d)
                        arcname = os.path.relpath(filepath, src)
                        new_zip.write(filepath, arcname)
                    for f in files:
                        filepath = os.path.join(root, f)
                        arcname = os.path.relpath(filepath, src)
                        new_zip.write(filepath, arcname)
        else:
            self.event_type = 50400
            compression = ':gz' if compress else ''
            base_dir = os.path.basename(os.path.normpath(ip.object_path))
            with tarfile.open(dst, 'w%s' % compression) as new_tar:
                new_tar.add(src, base_dir)

        shutil.rmtree(src)
        ip.object_path = dst
        ip.save()
        return dst

    def undo(self):
        pass

    def event_outcome_success(self):
        pass
