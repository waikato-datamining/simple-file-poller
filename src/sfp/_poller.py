import glob
import os
import traceback
from typing import Callable, List
from datetime import datetime
from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


GLOB_NAME_PLACEHOLDER = "{NAME}"
""" The glob placeholder for identifying other input files. """


def dummy_file_check(fname, poller):
    """
    Dummy file check method that lets all files pass.

    :param fname: the file to check
    :type fname: str
    :param poller: the poller triggered the processing
    :type poller: Poller
    :return: whether the file can be processed
    :rtype: bool
    """
    result = True
    poller.debug("Checking:", fname, "->", result)
    return result


def dummy_file_processing(fname, output_dir, poller):
    """
    Dummy file processing method. Simply creates a file with the ".done" extension in the output directory
    containing the original input file name.

    :param fname: the file to process
    :type fname: str
    :param output_dir: the output directory for writing additional files to
    :type output_dir: str
    :param poller: the poller triggered the processing
    :type poller: Poller
    :return: the list of files that were generated (absolute path names)
    :rtype: list
    """
    result = []

    poller.debug("Processing:", fname)

    out_fname = os.path.join(output_dir, os.path.basename(fname) + ".done")
    with open(out_fname, "w") as of:
        of.write(fname)

    result.append(out_fname)

    return result


LOGGING_TYPE_INFO = 1
LOGGING_TYPE_DEBUG = 2
LOGGING_TYPE_ERROR = 3


def simple_logging(logging_type, *args):
    """
    Just uses the print method to output the arguments.

    :param logging_type: the logging type
    :type logging_type: int
    :param args: the arguments to output
    """
    print(*args)


class FileCreatedHandler(FileSystemEventHandler):
    """
    Monitors only for file creations.
    """

    def __init__(self, poller):
        """

        :param poller: the Poller instance to use in case of event
        :type poller: Poller
        """
        super(FileCreatedHandler, self).__init__()
        self.poller = poller

    def on_created(self, event):
        """
        Gets called when a file gets created in the directory.

        :param event: the event
        """
        self.poller.debug("File created...")
        first = True
        while self.poller.is_busy:
            if first:
                first = False
                self.poller.debug("Poller busy, waiting...")
            sleep(0.1)
        maybe_more_files = True
        while maybe_more_files:
            file_list = self.poller.list_files()
            num_files = len(file_list)
            if (num_files == 0) or (num_files < self.poller.max_files):
                maybe_more_files = False
            if num_files > 0:
                self.poller.process_files(file_list)


class Parameters(object):
    """
    Dummy class that we abuse for storing custom parameters for the check_file and process_file methods.
    """
    pass


class Poller(object):
    """"
    Simple poller class that polls an input directory for files for processing and moves them (or deletes them)
    to the output directory. The temporary directory can be used for generating output files before moving them
    to the output directory itself (in case other processes are polling the output directory).
    """

    def __init__(self, input_dir=None, output_dir=None, tmp_dir=None, delete_input=False, continuous=False,
                 max_files=-1, extensions=None, other_input_files=None, delete_other_input_files=False,
                 blacklist_tries=3, poll_wait=1.0, use_watchdog=False, watchdog_check_interval=10.0,
                 verbose=False, progress=True, output_timestamp=True, output_num_files=False,
                 check_file=None, process_file=None, logging=simple_logging, params=Parameters()):
        """

        :param input_dir: The directory to poll for files to process.
        :type input_dir: str
        :param output_dir: The directory to move the processed files to (when not deleting them).
        :type output_dir: str
        :param tmp_dir: The temporary directory to write any generated files to first before moving them into the output directory (not required).
        :type tmp_dir: str
        :param delete_input: Whether to delete the input files rather than moving them to the output directory.
        :type delete_input: bool
        :param continuous: Whether to continuously poll for files or exit once no files available anymore.
        :type continuous: bool
        :param max_files: The maximum number of files retrieve with each poll, use <0 for no restrictions.
        :type max_files: int
        :param extensions: The list of extensions (lower case, with dots) to restrict the polling to, use None for accepting all files.
        :type extensions: list
        :param other_input_files: the glob expression for identifying other input files (replaces the {NAME} placeholder with the current name excl extension), None to not identify
        :type other_input_files: list
        :param delete_other_input_files: whether to delete the other input files identified via other_input_files or just move them to the output directory
        :type delete_other_input_files: bool
        :param blacklist_tries: The number of checks a file needs to fail before ending up in the black list of files to ignore when polling.
        :type blacklist_tries: int
        :param poll_wait: The number of seconds to wait between polls (when no files were processed).
        :type poll_wait: float
        :param use_watchdog: Whether to use time-based polling of watchdog.
        :type use_watchdog: bool
        :param watchdog_check_interval: the interval in seconds to perform a simple poll, in case a file creation event got missed
        :type watchdog_check_interval: float
        :param verbose: Whether to be more verbose with the logging output.
        :type verbose: bool
        :param progress: Whether to output progress information on the files being processed.
        :type progress: bool
        :param output_timestamp: whether to print a timestamp in the log messages
        :type output_timestamp: bool
        :param output_num_files: whether to output the number of files that are being processed ("x/y")
        :type output_num_files: bool
        :param check_file: the method to call for checking the files for validity
        :type check_file: object
        :param process_file: the method to call for processing a file
        :type process_file: object
        :param logging: the method to use for logging
        :type logging: object
        :param params: the object for encapsulating additional parameters for the check_file/process_file methods
        :type params: Parameters
        """

        self.input_dir = input_dir
        self.output_dir = output_dir
        self.tmp_dir = tmp_dir
        self.delete_input = delete_input
        self.continuous = continuous
        self.max_files = max_files
        self.extensions = extensions
        self.other_input_files = other_input_files
        self.delete_other_input_files = delete_other_input_files
        self.blacklist_tries = blacklist_tries
        self.poll_wait = poll_wait
        self.use_watchdog = use_watchdog
        self.watchdog_check_interval = watchdog_check_interval
        self.verbose = verbose
        self.progress = progress
        self.output_timestamp = output_timestamp
        self.output_num_files = output_num_files
        self.check_file = check_file
        self.process_file = process_file
        self.logging = logging
        self.is_listing_files = False
        self.is_processing_files = False
        self.params = params
        self._blacklist = dict()
        self._observer = None
        self._event_handler = None
        self._stopped = False

    @property
    def logging(self):
        """
        Returns the logging method.

        :return: the method in use
        :rtype: function
        """
        return self._logging

    @logging.setter
    def logging(self, fn):
        """
        Sets the logging function.

        :param fn: the method to use
        :type fn: function
        """
        self._logging = fn

    @property
    def check_file(self):
        """
        Returns the check file method.

        :return: the method in use
        :rtype: function
        """
        return self._check_file

    @check_file.setter
    def check_file(self, fn: Callable[[str, "Poller"], bool]):
        """
        Sets the check file function.

        :param fn: the method to use
        :type fn: function
        """
        self._check_file = fn

    @property
    def process_file(self):
        """
        Returns the process file method.

        :return: the method in use
        :rtype: function
        """
        return self._process_file

    @process_file.setter
    def process_file(self, fn: Callable[[str, str, "Poller"], List[str]]):
        """
        Sets the process file function.

        :param fn: the method to use
        :type fn: function
        """
        self._process_file = fn

    def debug(self, *args):
        """
        Outputs the arguments via 'log' if verbose is enabled.

        :param args: the debug arguments to output
        """
        if self.verbose:
            self._log(LOGGING_TYPE_DEBUG, *args)

    def info(self, *args):
        """
        Outputs the arguments via 'log' if progress is enabled.

        :param args: the info arguments to output
        """
        if self.progress:
            self._log(LOGGING_TYPE_INFO, *args)

    def error(self, *args):
        """
        Outputs the arguments via 'log'.

        :param args: the error arguments to output
        """
        self._log(LOGGING_TYPE_ERROR, *args)

    def _log(self, logging_type, *args):
        """
        Outputs the arguments via the logging function.

        :param logging_type: the logging type
        :type logging_type: int
        :param args: the arguments to output
        """
        if self._logging is not None:
            if self.output_timestamp:
                self._logging(logging_type, *("%s - " % str(datetime.now()), *args))
            else:
                self._logging(logging_type, *args)

    def keyboard_interrupt(self):
        """
        Prints an error message and stops the polling.
        """
        self.error("Interrupted, exiting")
        self.stop()

    def stop(self):
        """
        Stops the polling. Can be used by the check/processing methods in case of a fatal error.
        """
        self._stopped = True
        if self._observer is not None:
            self._observer.stop()
        self.is_processing_files = False
        self.is_listing_files = False

    @property
    def is_stopped(self):
        """
        Returns whether the polling got stopped, e.g., interrupted by the user.

        :return: whether it was stopped
        :rtype: bool
        """
        return self._stopped

    @property
    def is_busy(self):
        """
        Returns whether the poller is busy with I/O.

        :return: True if listing or processing files
        :rtype: bool
        """
        return self.is_listing_files or self.is_processing_files

    def _check(self):
        """
        For performing checks before starting the polling.
        Raises an exception if any check should fail.
        """

        if self.input_dir is None:
            raise Exception("No input directory provided!")
        if not os.path.exists(self.input_dir):
            raise Exception("Input directory does not exist: %s" % self.input_dir)
        if not os.path.isdir(self.input_dir):
            raise Exception("Input directory does not point to a directory: %s" % self.input_dir)

        if self.output_dir is None:
            raise Exception("No output directory provided!")
        if not os.path.exists(self.output_dir):
            raise Exception("Output directory does not exist: %s" % self.output_dir)
        if not os.path.isdir(self.output_dir):
            raise Exception("Output directory does not point to a directory: %s" % self.output_dir)

        if self.tmp_dir is not None:
            if not os.path.exists(self.tmp_dir):
                raise Exception("Temp directory does not exist: %s" % self.tmp_dir)
            if not os.path.isdir(self.tmp_dir):
                raise Exception("Temp directory does not point to a directory: %s" % self.tmp_dir)

        if self.extensions is not None:
            if len(self.extensions) == 0:
                raise Exception("Empty list provided for extensions!")
            for ext in self.extensions:
                if not ext.startswith("."):
                    raise Exception("All extensions must start with '.' (%s)!" % str(self.extensions))
                if ext != ext.lower():
                    raise Exception("Extensions must be lower case (%s)!" % str(self.extensions))

        if self.use_watchdog and not self.continuous:
            raise Exception("Watchdog only available in continuous mode!")

    def list_files(self):
        """
        Generates the list of files.

        :return: list of files
        :rtype: List[str]
        """

        if self.is_stopped:
            return

        self.is_listing_files = True
        file_list = []
        self.debug("Start listing files: %s" % self.input_dir)

        try:
            for file_name in os.listdir(self.input_dir):
                if self.is_stopped:
                    self.info("Stopped")
                    return

                file_path = os.path.join(self.input_dir, file_name)

                if os.path.isdir(file_path):
                    continue

                # monitored extension?
                if self.extensions is not None:
                    ext_lower = os.path.splitext(file_name)[1]
                    if ext_lower not in self.extensions:
                        self.debug("%s does not match extensions: %s" % (file_name, str(self.extensions)))
                        continue

                # file OK?
                if self.check_file is not None:
                    ok = self.check_file(file_path, self)
                    if ok:
                        # remove file from blacklist if it could be processed now
                        if file_path in self._blacklist:
                            del self._blacklist[file_path]
                        file_list.append(file_path)
                    else:
                        if file_path not in self._blacklist:
                            self._blacklist[file_path] = 1
                        else:
                            self._blacklist[file_path] = self._blacklist[file_path] + 1
                else:
                    file_list.append(file_path)

                # remove files that cannot be processed
                if len(self._blacklist) > 0:
                    remove_from_blacklist = []
                    for k in self._blacklist:
                        if self._blacklist[k] == self.blacklist_tries:
                            self.error("%s" % os.path.basename(k))
                            remove_from_blacklist.append(k)
                            try:
                                if self.delete_input:
                                    self.error("Flagged as incomplete %d times, deleting" % self.blacklist_tries)
                                    os.remove(k)
                                else:
                                    self.error("Flagged as incomplete %d times, skipping" % self.blacklist_tries)
                                    os.rename(k, os.path.join(self.output_dir, os.path.basename(k)))
                            except KeyboardInterrupt:
                                self.keyboard_interrupt()
                                return
                            except:
                                self.error(traceback.format_exc())

                    for k in remove_from_blacklist:
                        del self._blacklist[k]

                # reached limit for poll?
                if self.max_files > 0:
                    if len(file_list) == self.max_files:
                        self.debug("Reached maximum of %d files" % self.max_files)
                        break

            self.debug("Finished listing files")

        except KeyboardInterrupt:
            self.keyboard_interrupt()
            return
        except:
            self.error("Failed listing files!")
            self.error(traceback.format_exc())

        self.is_listing_files = False

        return file_list

    def process_files(self, file_list: List[str]):
        """
        Processes the polled files.

        :param file_list: the list of absolute file names to process (strings)
        :type file_list: list
        """

        if self.is_stopped:
            return

        self.is_processing_files = True
        num_files = len(file_list)

        try:
            for i, file_path in enumerate(file_list):
                if self.is_stopped:
                    self.error("Stopped")
                    return

                start_time = datetime.now()
                if self.output_num_files:
                    num_files_str = " %d/%d" % ((i + 1), num_files)
                else:
                    num_files_str = ""
                self.info("Start processing%s: %s" % (num_files_str, file_path))
                try:
                    if self.process_file is not None:
                        if self.tmp_dir is not None:
                            processed_list = self.process_file(file_path, self.tmp_dir, self)
                            for processed_path in processed_list:
                                self.debug("Moving processed %s to %s" % (processed_path, self.output_dir))
                                os.rename(processed_path, os.path.join(self.output_dir, os.path.basename(processed_path)))
                        else:
                            self.process_file(file_path, self.output_dir, self)

                    # input file
                    if self.delete_input:
                        self.debug("Deleting input%s: %s" % (num_files_str, file_path))
                        os.remove(file_path)
                    else:
                        self.debug("Moving input%s: %s -> %s" % (num_files_str, file_path, self.output_dir))
                        os.rename(file_path, os.path.join(self.output_dir, os.path.basename(file_path)))

                    # other input files?
                    if self.other_input_files is not None:
                        for other_input_file in self.other_input_files:
                            other_files = glob.glob(os.path.join(self.input_dir, other_input_file.replace(GLOB_NAME_PLACEHOLDER, os.path.splitext(file_path)[0])))
                            for other_file in other_files:
                                other_path = os.path.join(self.input_dir, other_file)
                                if self.delete_other_input_files:
                                    self.debug("Deleting other input%s: %s" % (num_files_str, other_path))
                                    os.remove(other_path)
                                else:
                                    self.debug("Moving other input%s: %s -> %s" % (num_files_str, other_path, self.output_dir))
                                    os.rename(other_path, os.path.join(self.output_dir, os.path.basename(other_path)))
                except KeyboardInterrupt:
                    self.keyboard_interrupt()
                    return
                except:
                    self.error("Failed processing%s: %s" % (num_files_str, file_path))
                    self.error(traceback.format_exc())

                end_time = datetime.now()
                processing_time = end_time - start_time
                processing_time = int(processing_time.total_seconds() * 1000)
                self.info("Finished processing%s: %d ms" % (num_files_str, processing_time))

        except KeyboardInterrupt:
            self.keyboard_interrupt()
            return
        except:
            self.error("Failed processing files!")
            self.error(traceback.format_exc())

        self.is_processing_files = False

    def _simple_poll(self):
        """
        Performs simple time-interval based polling.
        """

        while not self.is_stopped:
            file_list = self.list_files()

            # nothing found?
            if len(file_list) == 0:
                if self.continuous:
                    self.debug("Waiting %d seconds before next poll" % self.poll_wait)
                    sleep(self.poll_wait)
                    continue
                else:
                    self.debug("No files found, exiting")
                break

            self.process_files(file_list)

    def _watchdog_poll(self):
        """
        Starts a FileCreatedHandler for the input directory.
        """
        self._event_handler = FileCreatedHandler(poller=self)
        self._observer = Observer()
        self._observer.schedule(self._event_handler, self.input_dir)
        self._observer.start()
        try:
            count = 0.0
            while True:
                if (count == 0) or (count >= self.watchdog_check_interval):
                    if count == 0:
                        self.info("Initial check")
                    else:
                        self.info("Watchdog check interval reached")
                    count = 0.0
                    maybe_more_files = True
                    while maybe_more_files:
                        first = True
                        while self.is_busy:
                            if first:
                                first = False
                                self.debug("Poller busy, waiting...")
                            sleep(0.1)
                        file_list = self.list_files()
                        num_files = len(file_list)
                        if (num_files == 0) or (num_files < self.max_files):
                            maybe_more_files = False
                        if num_files > 0:
                            self.process_files(file_list)
                count += 0.1
                sleep(0.1)
        finally:
            self._observer.stop()
            self._observer.join()

    def poll(self):
        """
        Performs the polling.
        """

        self._stopped = False
        self._blacklist.clear()
        self._check()

        # output parameters
        self.debug("Polling parameters")
        self.debug("- Input dir: %s" % self.input_dir)
        self.debug("- Output dir: %s" % self.output_dir)
        if self.tmp_dir is not None:
            self.debug("- Temp dir: %s" % self.output_dir)
        if self.extensions is not None:
            self.debug("- Extensions: %s" % str(self.extensions))
        self.debug("- Continuous: %s" % str(self.continuous))
        self.debug("- Watchdog: %s" % str(self.use_watchdog))
        if self.use_watchdog:
            self.debug("- Watchdog check interval: %d seconds" % self.watchdog_check_interval)
        else:
            self.debug("- Poll wait interval: %d seconds" % self.poll_wait)

        if self.use_watchdog:
            self._watchdog_poll()
        else:
            self._simple_poll()
