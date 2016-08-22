import urllib2
import requests
import os
from earkcore.rest.restendpoint import RestEndpoint
from earkcore.filesystem.chunked import FileBinaryDataChunks
from earkcore.filesystem.chunked import default_reporter
from earkcore.rest.restresponsewrapper import ResponseWrapper
from requests_toolbelt.streaming_iterator import StreamingIterator

class UploadRestClient(object):
    """
    Upload REST client class
    """

    rest_endpoint = None

    def __init__(self, rest_endpoint, progress_reporter=default_reporter):
        """
        Constructor to initialise HDFS Rest Client with end point and progress reporter function
        @type       rest_endpoint: earkcore.rest.RestEndpoint
        @param      rest_endpoint: REST Endpoint (protocol, server-name, api)
        @type       progress_reporter: function
        @param      progress_reporter: Progress reporter function (default reporter writes to stdout)
        """
        self.rest_endpoint = rest_endpoint
        self.progress_reporter = progress_reporter

    def upload(self, local_file_path, rest_resource_path):
        """
        Add log message
        @type       local_file_path: string
        @param      local_file_path: Local file path
        @type       rest_resource_path: string
        @param      rest_resource_path: Resource file path (without leading slash!)
        @rtype:     string
        @return:    Relative HDFS path
        """
        file_resource_uri = self.rest_endpoint.get_resource_uri(rest_resource_path)
        if local_file_path is not None:
            # with open(local_file_path, 'r') as f:
            # strip path and extension from absolute file path to get filename
            filename = local_file_path.rpartition('/')[2]
            chunks = FileBinaryDataChunks(local_file_path, 65536, self.progress_reporter).chunks()
            file_size = os.path.getsize(local_file_path)
            streamer = StreamingIterator(file_size, chunks)
            content_type = 'multipart/form-data'
            s = requests.Session()
            s.auth = ('admin', 'admin')
            r = s.put(file_resource_uri.format(filename), data=streamer,
                      headers={'Content-Type': content_type})
            return ResponseWrapper(success=True, response=r)
        else:
            return ResponseWrapper(success=False)

    def get_string(self, rest_resource_path):
        """
        Read string from REST resource URI
        :param rest_resource_path: Rest path (part after base+api of the endpoint)
        :return: string response
        """
        resource_uri = self.rest_endpoint.get_resource_uri(rest_resource_path)
        return urllib2.urlopen(resource_uri).read()

def main():

    def custom_progress_reporter(percent):
        print "\rProgress:{percent:3.0f}%".format(percent=percent)

    rest_endpoint = RestEndpoint("http://10.0.0.26:5001", "essarch")
    upload_rest_client = UploadRestClient(rest_endpoint, custom_progress_reporter)

    aip_path = "/home/arch/ESSArch_Tools_20140407.tgz"
    rest_resource_path = "fileupload"

    # uncomment to test this class
    upload_rest_client.upload(aip_path, rest_resource_path)

if __name__ == "__main__":
    main()
