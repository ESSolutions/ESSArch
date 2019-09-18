import os
import shutil

from ESSArch_Core.fixity.transformation.backends.base import BaseTransformer
from ESSArch_Core.util import find_destination


class ContentTransformer(BaseTransformer):
    def transform(self, path):
        # move all dirs and files (except those specified in IP profile) to content

        structure = self.ip.get_structure()
        content_dir, content_name = find_destination('content', structure)
        content_path = os.path.join(self.ip.object_path, content_dir, content_name)

        reserved = [x['use'] for x in structure if 'use' in x]
        for f in os.listdir(path):
            if f not in reserved:
                shutil.move(os.path.join(path, f), content_path)
