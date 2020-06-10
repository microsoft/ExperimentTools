#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# stream_capture.py - used to echo (not redirect) a stream to a file.

class StreamCapture:
    '''
    usage:
        import sys
        from stream_capture import StreamCapture
        
        sys.stdout = StreamCapture(sys.stdout, "my_stdout_echo.txt")
    '''

    def __init__(self, stream, fn, flush_file=False, file=None):
        self.stream = stream
        self.log_file = file if file else open(fn, "wt")   
        self.flush_file = flush_file
        #self.buffer = stream.buffer
        #self.encoding = stream.encoding

    def write(self, data):
        # write to stream
        self.stream.write(data)
        self.stream.flush()

        # write to file
        if self.log_file:
            self.log_file.write(data)   
            if self.flush_file:
                self.log_file.flush()

    def flush(self):
        if self.log_file:
            self.log_file.flush()

    def close(self):
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        return self.stream  

        
       

       