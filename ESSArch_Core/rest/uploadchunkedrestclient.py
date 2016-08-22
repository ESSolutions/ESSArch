import requests
import os
import hashlib
from earkcore.filesystem.chunked import FileBinaryDataChunks
from earkcore.filesystem.chunked import default_reporter
from requests_toolbelt.multipart.encoder import MultipartEncoder
from retrying import retry

class UploadChunkedRestException(Exception):
    """
    There was an ambiguous exception that occurred while handling your
    upload.
    """
    def __init__(self, value):
        """
        Initialize UploadChunkedRestException with 
        `UploadChunkedRestClient` objects.
        """
        self.value = value
        super(UploadChunkedRestException, self).__init__(value)

class UploadError(UploadChunkedRestException):
    """An upload error occurred."""
    
class UploadWarning(UploadChunkedRestException):
    """An upload warning occurred."""

class UploadPostWarning(UploadChunkedRestException):
    """An upload post warning occurred."""

class UploadChunkedRestClient(object):
    """Upload chunked REST client class."""

    rest_endpoint = None

    def __init__(self, requests_session, rest_endpoint, progress_reporter=default_reporter):
        """
        Constructor to initialise Upload  Rest Client with end point and progress reporter function
        @type       requests.Session: class
        @param      requests_session: Requests session with authentication to REST service
        @type       string
        @param      rest_endpoint: REST URL (ex. https://servername/api/create_tmpworkarea_upload)
        @type       progress_reporter: function
        @param      progress_reporter: Progress reporter function (default reporter writes to stdout)
        """
        self.requests_session = requests_session
        self.rest_endpoint = rest_endpoint
        self.progress_reporter = progress_reporter

    def upload(self, local_file_path, ipuuid = None, chunk_size=1048576*10):
        """
        Add log message
        @type       local_file_path: string
        @param      local_file_path: Local file path
        @rtype:     string
        @return:    Relative HDFS path
        """
        if local_file_path is not None:
            # with open(local_file_path, 'r') as f:
            # strip path and extension from absolute file path to get filename
            hash = hashlib.md5()
            filename = local_file_path.rpartition('/')[2]
            file_size = os.path.getsize(local_file_path)
            if chunk_size > file_size:
                chunk_size = file_size
            chunks = FileBinaryDataChunks(local_file_path, chunk_size, self.progress_reporter).chunks()
            num = 0
            offset_start = 0
            offset_stop = chunk_size-1
            upload_id = ''
            for chunk in chunks:
                hash.update(chunk) 
                if num == 0:
                    HTTP_CONTENT_RANGE = 'bytes %s-%s/%s' % (offset_start, offset_stop, file_size)
                    m = MultipartEncoder(
                      fields={'the_file': (filename, chunk, 'application/octet-stream'),
                             }
                      )
                else:
                    offset_start = offset_stop + 1
                    offset_stop = offset_stop + chunk_size
                    if offset_stop > file_size:
                        offset_stop = file_size - 1
                        #print 'last offset_stop: %s file_size: %s' % (offset_stop, file_size)
                    HTTP_CONTENT_RANGE = 'bytes %s-%s/%s' % (offset_start, offset_stop, file_size)
                    m = MultipartEncoder(
                      fields={'upload_id': upload_id,
                              'the_file': (filename, chunk, 'application/octet-stream'),
                             }
                      )
                headers={'Content-Type': m.content_type,
                         'Content-Range': HTTP_CONTENT_RANGE}
                try:
                    #r = self.requests_session.post(self.rest_endpoint, data=m, headers=headers)
                    r = self.requests_post(self.rest_endpoint, data=m, headers=headers)
                except UploadPostWarning as e:
                    raise UploadError(e)
                r_json = r.json()
                upload_id = r_json['upload_id']
                offset = r_json['offset']
                expires = r_json['expires']
                #print 'upload_id: %s, c_num: %s, offset: %s' % (upload_id, num, offset)
                num += 1 
            m = MultipartEncoder(
              fields={'upload_id': upload_id,
                      'md5': hash.hexdigest(),
                      'ipuuid': ipuuid
                     }
              )
            headers={'Content-Type': m.content_type}
            try:
                #r = self.requests_session.post(self.rest_endpoint+'_complete', data=m, headers=headers)
                r = self.requests_post(self.rest_endpoint+'_complete', data=m, headers=headers)
            except UploadPostWarning as e:
                raise UploadError(e)

        return 'Success to upload %s' % local_file_path

    @retry(stop_max_attempt_number=5, wait_fixed=60000)
    def requests_post(self, rest_endpoint, data, headers):
        """
        Post data
        @type       string
        @param    rest_endpoint: URL
        @type       MultipartEncoder
        @param    data
        @type       dict
        @param    headers
        @rtype:     string
        @return:    requests return object
        """
        r = self.requests_session.post(rest_endpoint, data=data, headers=headers)
        if not r.status_code == 200:
            e = [r.status_code, r.reason, r.text]
            msg = 'Problem to upload chunk, (retrying), error: %s' % (e)
            print msg
            raise UploadPostWarning(e)
        return r

def main():

    def custom_progress_reporter(percent):
        print "\rProgress:{percent:3.0f}%".format(percent=percent)

    rest_endpoint = "http://10.0.0.26:5001/api/create_tmpworkarea_upload"
    from requests.packages.urllib3.exceptions import InsecureRequestWarning, InsecurePlatformWarning
    requests.packages.urllib3.disable_warnings(InsecurePlatformWarning)
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    requests_session = requests.Session()
    requests_session.auth = ('admin', 'admin')
    upload_rest_client = UploadChunkedRestClient(requests_session, rest_endpoint, custom_progress_reporter)

    local_file_path = "/home/arch/ESSArch_Server_install_201405191323.tgz"

    # uncomment to test this class
    print upload_rest_client.upload(local_file_path)

if __name__ == "__main__":
    main()
