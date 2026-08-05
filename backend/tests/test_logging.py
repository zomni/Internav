import logging

from app.infrastructure.log.middleware import TraceIDMiddleware
from app.infrastructure.log.setup import (
    TraceIDFilter,
    get_audit_logger,
    get_trace_id,
    set_trace_id,
    setup_logging,
)


class TestTraceIDFilter:
    def test_sets_default_when_missing(self):
        filter_ = TraceIDFilter()
        rec = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        assert filter_.filter(rec)
        assert rec.trace_id == "-"

    def test_passes_existing_trace_id(self):
        filter_ = TraceIDFilter()
        rec = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        rec.trace_id = "abc123"
        assert filter_.filter(rec)
        assert rec.trace_id == "abc123"

    def test_uses_global_trace_id(self):
        set_trace_id("global-42")
        filter_ = TraceIDFilter()
        rec = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        filter_.filter(rec)
        assert rec.trace_id == "global-42"
        set_trace_id("")


class TestGetSetTraceID:
    def test_round_trip(self):
        set_trace_id("test-trace")
        assert get_trace_id() == "test-trace"
        set_trace_id("")


class TestSetupLogging:
    def test_sets_root_level(self):
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

    def test_adds_handler(self):
        setup_logging("INFO")
        root = logging.getLogger()
        assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    def test_default_level(self):
        setup_logging()
        assert logging.getLogger().level == logging.INFO


class TestAuditLogger:
    def test_returns_logger_with_audit_prefix(self):
        audit = get_audit_logger("test")
        assert audit.name == "audit.test"
        assert not audit.propagate

    def test_has_handler(self):
        audit = get_audit_logger("test_handler")
        assert len(audit.handlers) > 0


class TestTraceIDMiddleware:
    def test_generates_trace_id(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.add_middleware(TraceIDMiddleware)

        @app.get("/ping")
        def ping():
            return {"ok": True}

        with TestClient(app) as client:
            resp = client.get("/ping")
            assert resp.status_code == 200
            assert "x-trace-id" in resp.headers
            assert len(resp.headers["x-trace-id"]) == 16

    def test_passes_client_trace_id(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.add_middleware(TraceIDMiddleware)

        @app.get("/ping")
        def ping():
            return {"ok": True}

        with TestClient(app) as client:
            resp = client.get("/ping", headers={"X-Trace-ID": "client-trace"})
            assert resp.headers["x-trace-id"] == "client-trace"
