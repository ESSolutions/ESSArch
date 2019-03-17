import os
import re

from ESSArch_Core.fixity.transformation.backends.base import BaseTransformer

REPEATED_PATTERN = r'\.(\w+)(\.(\1))+'


class RepeatedExtensionTransformer(BaseTransformer):
    def transform(self, path):
        new_path = re.sub(REPEATED_PATTERN, '.\\1', path)
        os.rename(path, new_path)
