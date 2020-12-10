# simple-file-poller
Simple Python 3 library for file polling.

## Installation

Install via pip:

```
pip install simple-file-poller
```

## Usage

The `sfp.Poller` class is used to poll for files to process.

As a minimum, the `input_dir` and `output_dir` directories need to 
get supplied.

You can choose between two types of polling: *simple* (default) or 
*[watchdog](https://github.com/gorakhargosh/watchdog)-based* one 
(`use_watchdog = True`). The simple approach merely checks the input 
directory every `poll_wait` seconds for new files. The watchdog 
approach reacts to *FILE_CREATED* events in the input directory 
to trigger the listing of files. The watchdog approach should be 
used in order to reduce latency within a pipeline of file-processing 
applications. Due to potential race conditions (e.g., when pairs of 
files need to be processed but the second appears slightly after the 
first one triggered the event already), some files may not get 
listed/processed. Hence, the poller will check in watchdog mode every 
`watchdog_check_interval` seconds whether there are not any files 
present in the input directory after all. Of course, watchdog mode 
is only available in conjunction with `continuous` mode.

By default, input files get moved to the output directory once process. 
With the `delete_input` option, you can remove them instead (e.g., if 
it is not necessary to keep them).

What kind of files are being included in the poll depends on their extension 
(when using `None` for `extensions` then all files get included).

By supplying a `check_file` method (signature: `fname:str, poller:Poller`) you 
can ensure that you only process valid files. E.g., with the 
[python-image-complete](https://pypi.org/project/python-image-complete/)
library you can determine whether an image is valid, i.e., fully written. 
See below for an example. 

If a file fails the check, it gets put on an internal blacklist. If it fails 
more than `blacklist_tries` times, it will get permanently excluded from 
processing (either moved to the output directory or deleted).

Since checks can take quite a long time, you may want to limit the batch size
of files queued for processing by setting a value greater than 0 for `max_files`.
Otherwise the process may look like it has stopped working when a large number
of files are present in the input directory and no output is coming out. 

The `process_file` method (signature: `fname:str, output_dir:str, poller:Poller`) 
is used for performing the actual processing of a file, e.g., applying a deep
learning classification model to an image to obtain a label.  

By specifying `tmp_dir`, all output files get generated in that directory before being
automatically moved into the actual `output_dir`. That avoids other processes that
are monitoring or polling for files in the output directory to spring into action
before the files have been fully written. 

The input directory may contain more than one file per ID (but with differing file
extensions) and if these should get moved to the output directory, then this can
be achieved with the `other_input_files` [glob](https://docs.python.org/3/library/glob.html) 
definition. The `{NAME}` placeholder, representing the current file being processed
(without its extension), can be used in that expression. For example, when processing
all `.jpg` files with the `process_file` method and all `.txt` and `.xml` should get
moved as well then use `["{NAME}.txt", "{NAME}.xml]` for `other_input_files`. If you
want to delete these files instead of moving them, then set `delete_other_input_files` 
to `True`. 

The `params` object can be used to attach parameters that are used by the 
`check_file` and `process_file` methods. By setting attributes in this
object you avoid the danger of accidentally replacing attributes that
were introduced in the Poller class at a later stage.

## Custom file check

The following example looks for JPG and PNG files in `/home/fracpete/poll/in/` and will
write dummy output files to the temp directory `/home/fracpete/poll/tmp/` before
moving them to `/home/fracpete/poll/tmp/`. A maximum of 3 files is processed at 
a time. It uses a custom check method to ensure that the images have been completely
written to disk before attempting to process them. Though PNG and JPG images
get processed, only JPG images get checked (`poller.params.dont_check_ext`).

```python
import os
from sfp import Poller, Parameters, dummy_file_processing
from image_complete.auto import is_image_complete

def image_complete(fname, poller):
    ext = os.path.splitext(fname)[1]
    if ext in poller.params.dont_check_ext:
        poller.debug("Not checking extension: %s" % ext)
        result = True
    else:
        result = is_image_complete(fname)
    poller.debug("Image complete:", fname, "->", result)
    return result

params = Parameters()
params.dont_check_ext = [".png"]

p = Poller(
    input_dir="/home/fracpete/poll/in/",
    output_dir="/home/fracpete/poll/out/",
    tmp_dir="/home/fracpete/poll/tmp/",
    continuous=True,
    max_files=3,
    check_file=image_complete,
    process_file=dummy_file_processing,
    extensions=[".jpg", ".png"],
    params=params)
p.poll()
print("Stopped?", p.is_stopped())
```

## Custom logging

By suppplying a method to the `logging` option, you can custom the logging
that occurs via the `info`, `debug` and `error` method calls of the Poller. 
The example below uses the Python logging framework.  

```python
from sfp import Poller, LOGGING_TYPE_INFO, LOGGING_TYPE_DEBUG, LOGGING_TYPE_ERROR
import logging

_logger = None
def custom_logging(*args):
    global _logger
    if _logger is None:
        logging.basicConfig()
        _logger = logging.getLogger("sfp")
        _logger.setLevel(logging.DEBUG)
    str_args = [str(x) for x in args]
    if type == LOGGING_TYPE_ERROR:
        _logger.error(" ".join(str_args))
    elif type == LOGGING_TYPE_DEBUG:
        _logger.debug(" ".join(str_args))
    else:
        _logger.info(" ".join(str_args))

p = Poller()
# ... setting more options
p.logging = custom_logging
p.output_timestamp = False # the Python logging framework should handle that instead
p.poll()
```
