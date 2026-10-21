"""#96 LOG_EXCEPTION_AND_FORMAT_FAILOPEN_LEAK: the logging layer is fail-closed.

A synthetic Google key (no real credential) must not reach any handler output or stderr through:
  * logger.exception / exc_info (traceback text),
  * stack_info,
  * a malformed %-format (logging.handleError used to print the raw args),
  * a broken redactor (it raises) or a broken traceback renderer: the record is withheld, not passed on raw.
"""
import contextlib
import io
import logging
import unittest
from unittest import mock

from omni_prod import secret_redaction

KEY = 'AIza' + 'SyD3m0x9Q7aB-cdEfGh_ijKLmnopQRstuv1'   # synthetic


class FailClosed(unittest.TestCase):
    def setUp(self):
        self._factory = logging.getLogRecordFactory()
        self.addCleanup(logging.setLogRecordFactory, self._factory)
        logging.setLogRecordFactory(logging.LogRecord)          # start from the stock factory every time
        secret_redaction.install_log_redaction()
        self.out = io.StringIO()
        handler = logging.StreamHandler(self.out)
        handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
        self.log = logging.getLogger(f'test.fail_closed.{self.id()}')
        self.log.handlers[:] = [handler]
        self.log.propagate = False
        self.log.setLevel(logging.DEBUG)
        raise_exc = logging.raiseExceptions
        self.addCleanup(setattr, logging, 'raiseExceptions', raise_exc)
        logging.raiseExceptions = True                           # handleError prints to stderr: the leak path

    def emit(self, fn):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            fn()
        return self.out.getvalue(), err.getvalue()

    def assertNoKey(self, out, err):
        self.assertNotIn(KEY, out)
        self.assertNotIn(KEY, err)

    def test_logger_exception_traceback_is_redacted(self):
        def go():
            try:
                raise RuntimeError(f'provider rejected ?key={KEY}')
            except RuntimeError:
                self.log.exception('call failed')
        out, err = self.emit(go)
        self.assertNoKey(out, err)
        self.assertIn('Traceback', out)                          # the traceback is kept, only the secret is not
        self.assertIn('RuntimeError: provider rejected ?key=[REDACTED]', out)

    def test_exc_info_tuple_from_outside_an_except_block_is_redacted(self):
        try:
            raise ValueError(KEY)
        except ValueError as exc:
            info = (type(exc), exc, exc.__traceback__)
        out, err = self.emit(lambda: self.log.error('later', exc_info=info))
        self.assertNoKey(out, err)

    def test_a_formatter_that_renders_exc_info_itself_gets_nothing_raw(self):
        class JsonLike(logging.Formatter):                       # e.g. a structured formatter: re-renders exc_info
            def format(self, record):
                tb = self.formatException(record.exc_info) if record.exc_info else (record.exc_text or '')
                return f'{{"msg": {record.getMessage()!r}, "exc": {tb!r}}}'
        self.log.handlers[0].setFormatter(JsonLike())

        def go():
            try:
                raise RuntimeError(KEY)
            except RuntimeError:
                self.log.exception('x')
        out, err = self.emit(go)
        self.assertNoKey(out, err)
        self.assertIn('RuntimeError: [REDACTED]', out)

    def test_stack_info_is_redacted(self):
        out, err = self.emit(lambda: self.log.info('where', stack_info=True))  # AIzaSyD3m0x9Q7aB-cdEfGh_ijKLmnopQRstuv1
        self.assertIn('Stack (most recent call last)', out)
        self.assertNoKey(out, err)

    def test_a_malformed_format_does_not_print_the_raw_args(self):
        out, err = self.emit(lambda: self.log.warning('count=%d', f'key={KEY}'))
        self.assertNoKey(out, err)
        self.assertIn(secret_redaction.UNFORMATTABLE.strip(), out)
        self.assertNotIn('Logging error', err)                   # nothing for handleError to print

    def test_a_broken_redactor_withholds_the_record(self):
        def boom(_text):
            raise RuntimeError('redactor broke')
        with mock.patch.object(secret_redaction, 'redact', boom):
            out, err = self.emit(lambda: self.log.error('key=%s', KEY))
            def go():
                try:
                    raise RuntimeError(KEY)
                except RuntimeError:
                    self.log.exception('x')
            out2, err2 = self.emit(go)
        self.assertNoKey(out + out2, err + err2)
        self.assertIn(secret_redaction.WITHHELD, out)
        self.assertNotIn('Traceback', out2)

    def test_a_broken_traceback_renderer_withholds_the_record(self):
        with mock.patch.object(logging.Formatter, 'formatException', side_effect=RuntimeError('render broke')):
            def go():
                try:
                    raise RuntimeError(KEY)
                except RuntimeError:
                    self.log.exception('x')
            out, err = self.emit(go)
        self.assertNoKey(out, err)
        self.assertIn(secret_redaction.WITHHELD, out)

    def test_an_ordinary_message_still_reads_normally(self):
        out, _ = self.emit(lambda: self.log.info('build %s ok in %.1fs', 'bld_1', 2.0))
        self.assertEqual(out, 'INFO build bld_1 ok in 2.0s\n')


if __name__ == '__main__':
    unittest.main()
