import logging
import shlex
from subprocess import PIPE, Popen

from ESSArch_Core.fixity.conversion.backends.base import BaseConverter
from ESSArch_Core.fixity.conversion.exceptions import InvalidFormat

logger = logging.getLogger('essarch.fixity.conversion.backends.openssl')


class OpenSSLConverter(BaseConverter):
    input_formats = [
        'application/x-pem-file',
        'application/x-pkcs12',
        'application/x-pkcs7-certificates',
        'application/x-x509-ca-cert',
    ]

    output_formats = [
        'application/x-pem-file',
        'application/x-pkcs12',
        'application/x-pkcs7-certificates',
        'application/x-x509-ca-cert',
    ]

    @classmethod
    def create_command(cls, in_file, out_file, in_fmt, out_fmt, cert_files=None, in_key=None, password=None):
        """
        Creates openssl file conversion command(s)

        Args:
            in_file (str): the input file
            out_file (str): the output file
            in_fmt (str): the input mimetype
            out_fmt (str): the output mimetype
            cert_files ([str]): certificate files used for -certfile
            in_key (str): key file sent to -inkey
            password (str): password sent to -passin or -passout

        Returns:
            A list or string of openssl file conversion commands
        """

        if cert_files is None:
            cert_files = []

        cert_files = ' '.join([f'-certfile {crt}' for crt in cert_files])
        in_key = f'-inkey {in_key}' if in_key is not None else ''
        passin = f'-passin {password}' if password is not None else ''
        passout = f'-passout {password}' if password is not None else ''

        if in_fmt == 'application/x-pem-file' and out_fmt == 'application/x-x509-ca-cert':
            # PEM TO DER
            cmd = f'openssl x509 -outform der -in {in_file} -out {out_file}'

        elif in_fmt == 'application/x-x509-ca-cert' and out_fmt == 'application/x-pem-file':
            # DER TO PEM
            cmd = f'openssl x509 -inform der -in {in_file} -out {out_file}'

        elif in_fmt == 'application/x-pem-file' and out_fmt == 'application/x-pkcs7-certificates':
            # PEM to PKCS #7
            cmd = f'openssl crl2pkcs7 -nocrl {cert_files} -out {out_file}'

        elif in_fmt == 'application/x-pkcs7-certificates' and out_fmt == 'application/x-pem-file':
            # PKCS #7 TO PEM
            cmd = f'openssl pkcs7 -print_certs -in {in_file} -out {out_file}'

        elif in_fmt == 'application/x-pem-file' and out_fmt == 'application/x-pkcs12':
            # PEM TO PKCS #12
            cmd = f'openssl pkcs12 -export {passout} -out {out_file} {in_key} -in {in_file} {cert_files}'

        elif in_fmt == 'application/x-pkcs12' and out_fmt == 'application/x-pem-file':
            # PKCS #12 TO PEM
            cmd = f'openssl pkcs12 -in {in_file} {passin} -out {out_file} -nodes'

        elif in_fmt == 'application/x-pkcs7-certificates' and out_fmt == 'application/x-pkcs12':
            # PKCS #7 TO PKCS #12

            cmd = [
                f'openssl pkcs7 -print_certs -in {in_file}',
                f'openssl pkcs12 -export {passout} {in_key} -out {out_file} {cert_files}',
            ]

        else:
            raise InvalidFormat("Invalid input/output formats")

        return cmd

    @classmethod
    def pipe_commands(cls, cmds):
        last_cmd = None

        for cmd in cmds:
            stdin = last_cmd.stdout if last_cmd is not None else None

            cmd = shlex.split(cmd)
            last_cmd = Popen(cmd, stdin=stdin, stdout=PIPE, stderr=PIPE)

        return last_cmd

    @classmethod
    def run_command(cls, cmd):
        if isinstance(cmd, list):
            return cls.pipe_commands(cmd)

        cmd = shlex.split(cmd)
        return Popen(cmd, stdout=PIPE, stderr=PIPE)

    def convert(self, input_file, output_file, in_fmt=None, out_fmt=None, **kwargs):
        cert_files = kwargs.pop('cert_files', None)
        in_key = kwargs.pop('in_key', None)
        password = kwargs.pop('password', None)

        cmd = self.create_command(input_file, output_file, in_fmt, out_fmt, cert_files, in_key, password)

        logger.debug(cmd)

        p = self.run_command(cmd)
        out, err = p.communicate()
        return out, err, p.returncode
