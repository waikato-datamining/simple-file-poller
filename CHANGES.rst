Changelog
=========

0.0.13 (2025-01-14)
-------------------

- added *stop file* support, i.e., when this file appears the poller will stop polling


0.0.12 (2025-01-07)
-------------------

- switched to underscores in project name
- added support for batch processing of files


0.0.11 (2024-09-13)
-------------------

- using `shutil.move` instead of `os.rename` to work across file-system boundaries


0.0.10 (2021-03-18)
-------------------

- added the `output_num_files` boolean property to the `Poller` class, which extends the logging output by
  outputting a `x/y` string as well (x=current file index, y=total number of files in a batch)


0.0.9 (2021-01-05)
------------------

- the `Poller.logging` property no longer returns the `check_file` method


0.0.8 (2020-12-11)
------------------

- fixed high CPU usage (ie constant polling) when using unlimited files to list (`max_files=0`)
- `poll_wait` and `watchdog_check_interval` are now float instead of int to allow for sub-second poll waits
- internal delays when poller is busy have been dropped from 1s to 0.1s


0.0.7 (2020-12-10)
------------------

- `keyboard_interrupt` method is now public


0.0.6 (2020-12-10)
------------------

- fixed race condition between watchdog reacting to new files and watchdog checking for files at specific intervals
- logging now distinguishes between DEBUG/INFO/ERROR levels
- keyboard interrupts via CTRL+C are now handled correctly
- in watchdog mode, an initial scan of the input directory is now performed, in case files were already present


0.0.5 (2020-12-10)
------------------

- added `params` object to allow attaching of arbitrary parameters to be used by the `check_file`
  and `process_file` methods; this avoids accidentally overriding Poller attributes that were
  introduced in later versions.


0.0.4 (2020-12-10)
------------------

- added support for using watchdog for reacting to file creation events, speeding up polling


0.0.3 (2020-12-04)
------------------

- `poll` method now skips directories, which could be listed if no extensions are supplied to restrict the polling.


0.0.2 (2020-12-03)
------------------

- added `other_input_files` glob list and `delete_other_input_files` to manage additional files that may
  reside in the input directory along side the actual files that are being processed.


0.0.1 (2020-12-02)
------------------

- initial release

