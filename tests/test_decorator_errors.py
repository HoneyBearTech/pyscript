"""Test pyscript decorator syntax error and eval-time exception reporting."""

from ast import literal_eval
import asyncio
from datetime import datetime as dt
from types import SimpleNamespace
from unittest.mock import mock_open, patch

import pytest

from custom_components.pyscript import trigger
from custom_components.pyscript.const import DOMAIN
from custom_components.pyscript.function import Function
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_STATE_CHANGED
from homeassistant.setup import async_setup_component


async def setup_script(hass, notify_q, now, source):
    """Initialize and load the given pyscript."""
    scripts = [
        "/hello.py",
    ]

    Function.hass = None

    with (
        patch("custom_components.pyscript.os.path.isdir", return_value=True),
        patch("custom_components.pyscript.glob.iglob", return_value=scripts),
        # This fixture deliberately uses a synthetic /hello.py for stable
        # traceback assertions; emulate the relative name of an in-root file.
        patch("custom_components.pyscript._relative_script_path", return_value="hello.py"),
        patch("custom_components.pyscript.global_ctx.open", mock_open(read_data=source)),
        patch("custom_components.pyscript.trigger.dt_now", return_value=now),
        patch("homeassistant.config.load_yaml_config_file", return_value={}),
        patch("custom_components.pyscript.open", mock_open(read_data=source)),
        patch("custom_components.pyscript.watchdog_start", return_value=None),
        patch("custom_components.pyscript.os.path.getmtime", return_value=1000),
        patch("custom_components.pyscript.global_ctx.os.path.getmtime", return_value=1000),
        patch(
            "custom_components.pyscript.install_requirements",
            return_value=None,
        ),
    ):
        assert await async_setup_component(hass, "pyscript", {DOMAIN: {}})

    #
    # I'm not sure how to run the mock all the time, so just force the dt_now()
    # trigger function to return the given list of times in now.
    #
    def return_next_time():
        if isinstance(now, list):
            if len(now) > 1:
                return now.pop(0)
            return now[0]
        return now

    trigger.__dict__["dt_now"] = return_next_time

    if notify_q:

        async def state_changed(event):
            var_name = event.data["entity_id"]
            if var_name != "pyscript.done":
                return
            value = event.data["new_state"].state
            await notify_q.put(value)

        hass.bus.async_listen(EVENT_STATE_CHANGED, state_changed)


async def wait_until_done(notify_q):
    """Wait for the done handshake."""
    return await asyncio.wait_for(notify_q.get(), timeout=4)


@pytest.mark.asyncio
async def test_decorator_errors(hass, caplog):
    """Test decorator syntax and run-time errors."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999), dt(2020, 7, 1, 11, 59, 59, 999999)],
        """
seq_num = 0

@time_trigger("startup")
def func_startup_sync(trigger_type=None, trigger_time=None):
    global seq_num

    seq_num += 1
    log.info(f"func_startup_sync setting pyscript.done = {seq_num}, trigger_type = {trigger_type}, trigger_time = {trigger_time}")
    pyscript.done = seq_num

@state_trigger("z + ")
def func1():
    pass

@event_trigger("some_event", "func(")
def func2():
    pass

@state_trigger("True")
@state_active("z = 1")
def func3():
    pass

@state_trigger("1 / int(pyscript.var1)")
def func5():
    pass

@state_trigger("False", ["False", "False", "pyscript.var1"])
@state_active("1 / pyscript.var1")
def func6():
    pass

@state_trigger("False", "False", ["pyscript.var7"])
def func7():
    global seq_num

    try:
        task.wait_until(state_trigger="z +")
    except SyntaxError as exc:
        log.error(exc)

    try:
        task.wait_until(event_trigger=["event", "z+"])
    except SyntaxError as exc:
        log.error(exc)

    try:
        task.wait_until(state_trigger="pyscript.var1 + 1")
    except TypeError as exc:
        log.error(exc)

    seq_num += 1
    pyscript.done = seq_num

@state_trigger("pyscript.var_done")
def func_wrapup():
    global seq_num

    seq_num += 1
    pyscript.done = seq_num

@state_trigger("z")
def func8():
    pass

""",
    )
    seq_num = 0

    seq_num += 1
    # fire event to start triggers, and handshake when they are running
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    assert literal_eval(await wait_until_done(notify_q)) == seq_num

    hass.states.async_set("pyscript.var1", 1)
    hass.states.async_set("pyscript.var1", 0)

    seq_num += 1
    hass.states.async_set("pyscript.var7", 1)
    assert literal_eval(await wait_until_done(notify_q)) == seq_num

    seq_num += 1
    hass.states.async_set("pyscript.var_done", 1)
    assert literal_eval(await wait_until_done(notify_q)) == seq_num

    assert "SyntaxError: invalid syntax" in caplog.text
    assert 'File "/hello.py", line 1, in file.hello.func1 @state_trigger()' in caplog.text
    assert "SyntaxError: '(' was never closed" in caplog.text
    assert 'File "/hello.py", line 1, in file.hello.func2 @event_trigger()' in caplog.text
    assert 'File "/hello.py", line 1, in file.hello.func3 @state_active()' in caplog.text
    assert (
        "trigger file.hello.func8: @state_trigger is not watching any variables; will never trigger"
        in caplog.text
    )
    assert (
        """File "/hello.py", line 1, in file.hello.func5 @state_trigger()
    1 / int(pyscript.var1)
    ~~^~~~~~~~~~~~~~~~~~~~
ZeroDivisionError: division by zero"""
        in caplog.text
    )

    assert (
        """File "/hello.py", line 1, in file.hello.func6 @state_active()
    1 / pyscript.var1
    ~~^~~~~~~~~~~~~~~
TypeError: unsupported operand type(s) for /: 'int' and 'StateVal'"""
        in caplog.text
    )

    # assert "unexpected EOF while parsing (file.hello.func7 state_trigger, line 1)" in caplog.text   # <= 3.9
    assert "invalid syntax (file.hello.func7 state_trigger, line 1)" in caplog.text
    assert 'can only concatenate str (not "int") to str' in caplog.text


@pytest.mark.asyncio
async def test_decorator_errors_missing_trigger(hass, caplog):
    """Test decorator syntax and run-time errors."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999)],
        """
@state_active("z + ")
def func4():
    pass
""",
    )
    assert (
        "func4 defined in file.hello: needs at least one trigger decorator (ie: event_trigger, mqtt_trigger, state_trigger, time_trigger, webhook_trigger)"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_trigger_expression_errors(hass, caplog, monkeypatch):
    """Legacy trigger expression errors should not stop trigger loops."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999), dt(2020, 7, 1, 11, 59, 59, 999999)],
        """
seq_num = 0

@time_trigger("startup")
def func_startup_sync(trigger_type=None, trigger_time=None):
    global seq_num

    seq_num += 1
    pyscript.done = seq_num

@event_trigger("test_event", "1 / int(arg1)")
def func1(arg1=None):
    global seq_num

    seq_num += 1
    pyscript.done = ["event", seq_num, arg1]

@state_trigger("1 / int(pyscript.var1)")
def func2(var_name=None, value=None):
    global seq_num

    seq_num += 1
    pyscript.done = ["state", seq_num, var_name, int(value)]
""",
    )

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    assert literal_eval(await wait_until_done(notify_q)) == 1

    hass.bus.async_fire("test_event", {"arg1": 0})
    await hass.async_block_till_done()
    assert notify_q.empty()

    hass.states.async_set("pyscript.var1", 0)
    await hass.async_block_till_done()
    assert notify_q.empty()

    hass.bus.async_fire("test_event", {"arg1": 1})
    assert literal_eval(await wait_until_done(notify_q)) == ["event", 2, 1]

    hass.states.async_set("pyscript.var1", 1)
    assert literal_eval(await wait_until_done(notify_q)) == ["state", 3, "pyscript.var1", 1]

    assert (
        """File "/hello.py", line 1, in file.hello.func1 @event_trigger()
    1 / int(arg1)
    ~~^~~~~~~~~~~
ZeroDivisionError: division by zero"""
        in caplog.text
    )

    assert (
        """File "/hello.py", line 1, in file.hello.func2 @state_trigger()
    1 / int(pyscript.var1)
    ~~^~~~~~~~~~~~~~~~~~~~
ZeroDivisionError: division by zero"""
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_errors_missing_arg(hass, caplog):
    """Test decorator syntax and run-time errors."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999)],
        """
@state_trigger
def func8():
    pass
""",
    )
    assert (
        "TypeError: function 'func8' defined in file.hello: decorator @state_trigger needs at least one argument"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_errors_missing_arg2(hass, caplog):
    """Test decorator syntax and run-time errors."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999)],
        """
@event_trigger
def func9():
    pass
""",
    )
    assert (
        "TypeError: function 'func9' defined in file.hello: decorator @event_trigger needs at least one argument"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_errors_bad_arg_type(hass, caplog):
    """Test decorator syntax and run-time errors."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999)],
        """
@state_trigger([None])
def func10():
    pass
""",
    )
    assert (
        "TypeError: function 'func10' defined in file.hello: decorator @state_trigger argument 1 should be a string, or list, or set"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_errors_bad_arg_type2(hass, caplog):
    """Test decorator syntax and run-time errors."""
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass,
        notify_q,
        [dt(2020, 7, 1, 10, 59, 59, 999999)],
        """
@state_trigger(False)
def func11():
    pass
""",
    )
    assert (
        "TypeError: function 'func11' defined in file.hello: decorator @state_trigger argument 1 should be a string"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_service_reload_error(hass, caplog):
    """Test using a reserved name generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@service
def reload():
    pass
""",
    )
    assert (
        "SyntaxError: function 'reload' defined in file.hello: @service conflicts with builtin service"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_service_state_active_extra_args(hass, caplog):
    """Test using extra args to state_active generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@state_active("arg1", "too many args")
def func4():
    pass
""",
    )
    assert (
        "TypeError: function 'func4' defined in file.hello: decorator @state_active got 2 arguments, expected 1"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_service_wrong_arg_type(hass, caplog):
    """Test using too many args with service an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@service(1)
def func5():
    pass
""",
    )
    assert (
        "TypeError: function 'func5' defined in file.hello: decorator @service argument 1 should be a string"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_time_trigger_wrong_arg_type(hass, caplog):
    """Test using wrong argument type generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@time_trigger("wrong arg type", 50)
def func6():
    pass
""",
    )
    assert (
        "TypeError: function 'func6' defined in file.hello: decorator @time_trigger argument 2 should be a string"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_kwargs(hass, caplog):
    """Test invalid keyword arguments generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@time_trigger("invalid kwargs", arg=10)
def func7():
    pass
""",
    )
    assert (
        "TypeError: function 'func7' defined in file.hello: decorator @time_trigger invalid keyword argument 'arg'"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_kwargs2(hass, caplog):
    """Test invalid keyword arguments generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@task_unique("invalid kwargs", arg=10)
def func7():
    pass
""",
    )
    assert (
        "TypeError: function 'func7' defined in file.hello: decorator @task_unique invalid keyword argument 'arg'"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_kwargs3(hass, caplog):
    """Test invalid keyword arguments type generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@state_trigger("abc.xyz", kwargs=10)
def func7():
    pass
""",
    )
    assert (
        "TypeError: function 'func7' defined in file.hello: decorator @state_trigger keyword 'kwargs' should be type dict"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_decorator_kwargs4(hass, caplog):
    """Test invalid keyword arguments type generates an error."""

    await setup_script(
        hass,
        None,
        dt(2020, 7, 1, 11, 59, 59, 999999),
        """
@state_trigger("abc.xyz", watch=10)
def func7():
    pass
""",
    )
    assert (
        "TypeError: function 'func7' defined in file.hello: decorator @state_trigger keyword 'watch' should be type list or set"
        in caplog.text
    )


# the example in #617, as written there (its lines end in "and "), as a single trigger and as one of several
ISSUE_617_SOURCE = (
    "_state_sensor = 'sensor.office_state'\n"
    "\n"
    '@state_trigger(f"""\n'
    "{_state_sensor} in ['recently occupied', 'unoccupied', 'dormant', 'unavailable'] and \n"
    "(sensor.octoprint_actual_tool0_temp == 'unavailable' or float(sensor.octoprint_actual_tool0_temp) <= 110) and \n"
    "(sensor.octoprint_actual_bed_temp == 'unavailable' or float(sensor.octoprint_actual_bed_temp) <= 110)\n"
    '""", state_hold_false=0)\n'
    "def should_turn_off():\n"
    "    pyscript.done = '617 single'\n"
    "\n"
    '@state_trigger("pyscript.never == \'1\'", f"""\n'
    "{_state_sensor}2 in ['recently occupied', 'unoccupied', 'dormant', 'unavailable'] and \n"
    "(sensor.printer2_tool0_temp == 'unavailable' or float(sensor.printer2_tool0_temp) <= 110) and \n"
    "(sensor.printer2_bed_temp == 'unavailable' or float(sensor.printer2_bed_temp) <= 110)\n"
    '""", state_hold_false=0)\n'
    "def should_turn_off_2():\n"
    "    pyscript.done = '617 several'\n"
)

TRIGGER_EXPR_SOURCE = r"""

@time_trigger("startup")
def func_startup():
    pyscript.done = "startup"

@state_trigger(" pyscript.a == '1'")
def func_space(value=None):
    pyscript.done = "space"

@state_trigger("\npyscript.b == '1'\n")
def func_newline(value=None):
    pyscript.done = "newline"

@state_trigger("\t pyscript.c == '1'\t")
def func_tab(value=None):
    pyscript.done = "tab"

@state_trigger('''
    pyscript.d == '1' and
    pyscript.e == '1'
''')
def func_multiline(value=None):
    pyscript.done = "multiline"

@state_trigger('''
    pyscript.m1 == '1' and  # first condition
    pyscript.m2 == '1'  # last condition
''')
def func_comments():
    pyscript.done = "comments"

@state_trigger("  pyscript.f  ", "\n pyscript.g == '1'")
def func_any(var_name=None):
    pyscript.done = var_name


@state_trigger("pyscript.k == '1' \\")
def func_backslash():
    pyscript.done = "backslash"

@state_trigger("k := pyscript.walrus == '1'")
def func_walrus():
    pyscript.done = "walrus"

# a bare tuple is one element of the any([...]), and a tuple is always true
@state_trigger("pyscript.t1 == 'no', pyscript.t1 == 'nope'", "pyscript.t2 == '1'")
def func_tuple(var_name=None):
    pyscript.done = f"tuple {var_name}"

@state_trigger(" pyscript.h == '1'")
@state_active('''
    pyscript.active == '1' and
    pyscript.active2 == '1'
''')
def func_active():
    pyscript.done = "active"

@event_trigger("test_event", "\n arg1 == 1 and\n arg2 == 2 \n")
def func_event(arg1=None, arg2=None):
    pyscript.done = "event"

@mqtt_trigger("test/topic", "\n payload == 'on' and  # the payload\n topic == 'test/topic'\n")
def func_mqtt():
    pyscript.done = "mqtt"

@state_trigger("pyscript.w1 == '1'")
def func_wait():
    task.wait_until(state_trigger=" pyscript.w2 == 'go' and\n pyscript.w2b == 'go'  # both\n", state_check_now=False)
    pyscript.done = "waited state"

@state_trigger("pyscript.w3 == '1'")
def func_wait_event():
    task.wait_until(event_trigger=["test_wait", "\t arg1 == 2 and\n arg2 == 3 "])
    pyscript.done = "waited event"

@state_trigger("pyscript.w4 == '1'")
def func_wait_mqtt():
    task.wait_until(mqtt_trigger=["test/wait", "\n payload == 'go' or\n payload == 'went'\n"])
    pyscript.done = "waited mqtt"

@state_trigger("pyscript.s == '1'")
def func_syntax():
    for expr in [" a b", "\n  a b \n", "\n  x == 1 and\n", "  # nothing", "a) or (b"]:
        try:
            task.wait_until(state_trigger=expr)
        except SyntaxError as exc:
            pyscript.done = [exc.msg, exc.lineno, exc.offset, exc.end_lineno, exc.end_offset, exc.text]
"""


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True], ids=["decorators", "legacy_decorators"])
async def test_trigger_expression_whitespace(hass, caplog, monkeypatch, legacy):
    """Trigger expressions may start and end with blanks and run over several lines without brackets."""
    if legacy:
        monkeypatch.setenv("NODM", "1")
    mqtt_handlers = {}

    async def mqtt_subscribe(_hass, topic, handler, **_kwargs):
        mqtt_handlers[topic] = handler
        return lambda: None

    async def mqtt_message(topic, payload):
        await mqtt_handlers[topic](SimpleNamespace(topic=topic, payload=payload, qos=0, retain=False))

    monkeypatch.setattr("homeassistant.components.mqtt.async_subscribe", mqtt_subscribe)
    notify_q = asyncio.Queue(0)
    await setup_script(
        hass, notify_q, [dt(2020, 7, 1, 10, 59, 59, 999999)], ISSUE_617_SOURCE + TRIGGER_EXPR_SOURCE
    )
    assert ("Using legacy decorators" in caplog.text) == legacy

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    assert await wait_until_done(notify_q) == "startup"

    async def check(expected):
        assert await wait_until_done(notify_q) == expected

    async def check_none():
        await hass.async_block_till_done()
        assert notify_q.empty()

    hass.states.async_set("pyscript.a", "1")
    await check("space")
    hass.states.async_set("pyscript.b", "1")
    await check("newline")
    hass.states.async_set("pyscript.c", "1")
    await check("tab")
    hass.states.async_set("pyscript.d", "1")
    await check_none()
    hass.states.async_set("pyscript.e", "1")
    await check("multiline")
    hass.states.async_set("pyscript.m1", "1")
    await check_none()
    hass.states.async_set("pyscript.m2", "1")
    await check("comments")

    # a state name with blanks around it means "any change", and the name is exact
    hass.states.async_set("pyscript.f", "x")
    await check("pyscript.f")
    hass.states.async_set("pyscript.g", "1")
    await check("pyscript.g")

    # #617: false first (state_hold_false=0), then true when the last state changes
    for suffix, temps, expected in (
        ("", "octoprint_actual", "617 single"),
        ("2", "printer2", "617 several"),
    ):
        hass.states.async_set(f"sensor.office_state{suffix}", "occupied")
        hass.states.async_set(f"sensor.{temps}_tool0_temp", "100")
        hass.states.async_set(f"sensor.{temps}_bed_temp", "120")
        await check_none()
        hass.states.async_set(f"sensor.office_state{suffix}", "unoccupied")
        await check_none()
        hass.states.async_set(f"sensor.{temps}_bed_temp", "100")
        await check(expected)

    hass.states.async_set("pyscript.k", "1")
    await check("backslash")
    hass.states.async_set("pyscript.walrus", "1")
    await check("walrus")
    hass.states.async_set("pyscript.t1", "x")
    await check("tuple pyscript.t1")

    hass.states.async_set("pyscript.h", "1")
    await check_none()
    hass.states.async_set("pyscript.active", "1")
    hass.states.async_set("pyscript.active2", "1")
    hass.states.async_set("pyscript.h", "0")
    hass.states.async_set("pyscript.h", "1")
    await check("active")

    hass.bus.async_fire("test_event", {"arg1": 1, "arg2": 0})
    await check_none()
    hass.bus.async_fire("test_event", {"arg1": 1, "arg2": 2})
    await check("event")

    await mqtt_message("test/topic", "off")
    await check_none()
    await mqtt_message("test/topic", "on")
    await check("mqtt")

    # task.wait_until: keep poking until the function is waiting
    async def poke_until_done(start, poke, expected):
        hass.states.async_set(start, "1")
        for i in range(100):
            if not notify_q.empty():
                break
            await poke(i)
            await asyncio.sleep(0.02)
        await check(expected)

    async def poke_state(i):
        hass.states.async_set("pyscript.w2b", "go")
        hass.states.async_set("pyscript.w2", f"stop{i}")
        hass.states.async_set("pyscript.w2", "go")

    async def poke_event(_i):
        hass.bus.async_fire("test_wait", {"arg1": 2, "arg2": 0})
        hass.bus.async_fire("test_wait", {"arg1": 2, "arg2": 3})

    async def poke_mqtt(_i):
        if "test/wait" in mqtt_handlers:
            await mqtt_message("test/wait", "went")

    await poke_until_done("pyscript.w1", poke_state, "waited state")
    await poke_until_done("pyscript.w3", poke_event, "waited event")
    await poke_until_done("pyscript.w4", poke_mqtt, "waited mqtt")

    # a script catching the SyntaxError reads the line, place and text of the expression as written
    hass.states.async_set("pyscript.s", "1")
    for expected in [
        ["invalid syntax. Perhaps you forgot a comma?", 1, 2, 1, 5, " a b"],
        ["invalid syntax. Perhaps you forgot a comma?", 2, 3, 2, 6, "  a b "],
        ["invalid syntax", 2, 12, 2, 13, "  x == 1 and"],
        ["expression is empty", 1, 1, 1, 2, "  # nothing"],
        ["unmatched ')'", 1, 2, 1, 3, "a) or (b"],
    ]:
        assert literal_eval(await wait_until_done(notify_q)) == expected

    assert "IndentationError" not in caplog.text


TRIGGER_COMMENT_SOURCE = r"""
@time_trigger("startup")
def func_startup():
    pyscript.done = "startup"

@state_trigger("pyscript.c1 == '1' # first condition\n", "pyscript.c2 == '1'\t# last condition")
def func_comments(var_name=None):
    pyscript.done = var_name

@state_trigger("  pyscript.c3 == '1'  # only condition\n")
def func_single_comment():
    pyscript.done = "single"

@state_trigger("pyscript.w1 == '1'")
def func_wait_first():
    task.wait_until(state_trigger=["pyscript.w2 == 'go' # first\n", "pyscript.w3 == 'go' # last"], state_check_now=False)
    pyscript.done = "waited first"

@state_trigger("pyscript.w4 == '1'")
def func_wait_last():
    task.wait_until(state_trigger=["pyscript.w2 == 'go' # first\n", "pyscript.w3 == 'go' # last"], state_check_now=False)
    pyscript.done = "waited last"
"""


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True], ids=["decorators", "legacy_decorators"])
async def test_trigger_expression_comments(hass, caplog, monkeypatch, legacy):
    """A # comment ending a trigger expression never swallows what follows it."""
    if legacy:
        monkeypatch.setenv("NODM", "1")
    notify_q = asyncio.Queue(0)
    await setup_script(hass, notify_q, [dt(2020, 7, 1, 10, 59, 59, 999999)], TRIGGER_COMMENT_SOURCE)
    assert ("Using legacy decorators" in caplog.text) == legacy

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    assert await wait_until_done(notify_q) == "startup"

    hass.states.async_set("pyscript.c1", "1")
    assert await wait_until_done(notify_q) == "pyscript.c1"
    hass.states.async_set("pyscript.c2", "1")
    assert await wait_until_done(notify_q) == "pyscript.c2"
    hass.states.async_set("pyscript.c3", "1")
    assert await wait_until_done(notify_q) == "single"

    # task.wait_until with a list: the first entry ends in a comment, the last entry is a comment
    for trig, entity, expected in (
        ("pyscript.w1", "pyscript.w2", "waited first"),
        ("pyscript.w4", "pyscript.w3", "waited last"),
    ):
        hass.states.async_set(trig, "1")
        for i in range(100):
            if not notify_q.empty():
                break
            hass.states.async_set(entity, f"stop{i}")
            hass.states.async_set(entity, "go")
            await asyncio.sleep(0.02)
        assert await wait_until_done(notify_q) == expected

    assert "SyntaxError" not in caplog.text


TRIGGER_EXPR_ERROR_SOURCE = r"""
@state_trigger("\n   \t(1 +\n  * 2)\n")
def func1():
    pass

@event_trigger("some_event", "  \n a b")
def func2():
    pass

@state_trigger(" a b")
def func3():
    pass

@state_trigger("\n  pyscript.x == '1' and\n")
def func4():
    pass

@state_trigger("pyscript.x == '1' and (\n  pyscript.y == '1'")
def func5():
    pass

@state_trigger("  # nothing here")
def func6():
    pass

@state_trigger("pyscript.x == '1') or (pyscript.y == '1'")
def func7():
    pass

@state_trigger("pyscript.x == '1'", "pyscript.x == '2' or\n  pyscript.y = 1")
def func8():
    pass

@state_active(" pyscript.x = 1")
@state_trigger("pyscript.x")
def func9():
    pass

@mqtt_trigger("some/topic", "\n payload == 1 and\n  (a b)")
def func10():
    pass

@webhook_trigger("some_hook", " a b")
def func11():
    pass

@state_trigger(" 1 / int(pyscript.r1) > 0")
def func12():
    pass

@state_trigger('''
    pyscript.r2 == '1' and
    1 / int(pyscript.r3) > 0
''')
def func13():
    pass

@state_trigger("pyscript.r4 == '1'", '''
    pyscript.r4 == '2' or
    1 / int(pyscript.r5) > 0
''')
def func14():
    pass
"""


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy", [False, True], ids=["decorators", "legacy_decorators"])
async def test_trigger_expression_error_messages(hass, caplog, monkeypatch, legacy):
    """Errors in a trigger expression show the expression as written, pointing at the problem."""
    if legacy:
        monkeypatch.setenv("NODM", "1")
    await setup_script(hass, None, [dt(2020, 7, 1, 10, 59, 59, 999999)], TRIGGER_EXPR_ERROR_SOURCE)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    hass.states.async_set("pyscript.r1", "0")
    hass.states.async_set("pyscript.r3", "0")
    hass.states.async_set("pyscript.r2", "1")
    hass.states.async_set("pyscript.r5", "0")
    await hass.async_block_till_done()

    for expected in [
        # syntax errors: on the first line one place to the left, later lines unchanged
        """line 3, in file.hello.func1 @state_trigger()
    * 2)
    ^
SyntaxError: invalid syntax""",
        """line 2, in file.hello.func2 @event_trigger()
    a b
SyntaxError: invalid syntax. Perhaps you forgot a comma?""",
        """line 1, in file.hello.func3 @state_trigger()
    a b
SyntaxError: invalid syntax. Perhaps you forgot a comma?""",
        # cut short: at the last character of the last line that isn't blank
        """line 2, in file.hello.func4 @state_trigger()
    pyscript.x == '1' and
                        ^
SyntaxError: invalid syntax""",
        """line 1, in file.hello.func5 @state_trigger()
    pyscript.x == '1' and (
                          ^
SyntaxError: '(' was never closed""",
        """line 1, in file.hello.func6 @state_trigger()
    # nothing here
SyntaxError: expression is empty""",
        """line 1, in file.hello.func7 @state_trigger()
    pyscript.x == '1') or (pyscript.y == '1'
                     ^
SyntaxError: unmatched ')'""",
        # several entries: the line of the any([...]) text, as before
        """line 3, in file.hello.func8 @state_trigger()
    pyscript.y = 1
               ^
SyntaxError: invalid syntax""",
        """line 1, in file.hello.func9 @state_active()
    pyscript.x = 1
    ^^^^^^^^^^
SyntaxError: cannot assign to attribute here. Maybe you meant '==' instead of '='?""",
        """line 3, in file.hello.func10 @mqtt_trigger()
    (a b)
     ^^^
SyntaxError: invalid syntax. Perhaps you forgot a comma?""",
        """line 1, in file.hello.func11 @webhook_trigger()
    a b
SyntaxError: invalid syntax. Perhaps you forgot a comma?""",
        # errors while the expression runs
        """line 1, in file.hello.func12 @state_trigger()
    1 / int(pyscript.r1) > 0
    ~~^~~~~~~~~~~~~~~~~~
ZeroDivisionError: division by zero""",
        """line 3, in file.hello.func13 @state_trigger()
    1 / int(pyscript.r3) > 0
    ~~^~~~~~~~~~~~~~~~~~
ZeroDivisionError: division by zero""",
        """line 4, in file.hello.func14 @state_trigger()
    1 / int(pyscript.r5) > 0
    ~~^~~~~~~~~~~~~~~~~~
ZeroDivisionError: division by zero""",
    ]:
        assert f'File "/hello.py", {expected}' in caplog.text
    assert "IndentationError" not in caplog.text
