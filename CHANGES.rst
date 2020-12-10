Changelog
=========

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

