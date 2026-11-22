"""Unit tests for time trigger functions."""

import ast as ast_module
from datetime import datetime as dt, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.pyscript.const import CONFIG_ENTRY, DOMAIN
from custom_components.pyscript.eval import AstEval
from custom_components.pyscript.function import Function
from custom_components.pyscript.global_ctx import GlobalContext, GlobalContextMgr
from custom_components.pyscript.trigger import TrigTime

parseDateTimeTests = [
    ["2019/9/12 13:45", 0, dt(2019, 9, 12, 13, 45, 0, 0)],
    ["9/12 13:45", 0, dt(2019, 9, 12, 13, 45, 0, 0)],
    ["2019/9/12 13:45:23", 0, dt(2019, 9, 12, 13, 45, 23, 0)],
    ["2019/9/12", 0, dt(2019, 9, 12, 0, 0, 0, 0)],
    ["2019/9/12 noon", 1, dt(2019, 9, 12, 12, 0, 0, 0)],
    ["2019/9/12 noon+1 min", 2, dt(2019, 9, 12, 12, 1, 0, 0)],
    ["2019/9/12 noon +2.5min", 1, dt(2019, 9, 12, 12, 2, 30, 0)],
    ["2019/9/12 noon+3 hr", 4, dt(2019, 9, 12, 15, 0, 0, 0)],
    ["2019/9/12 noon - 30 sec", 3, dt(2019, 9, 12, 11, 59, 30, 0)],
    ["2019/9/12 midnight", 3, dt(2019, 9, 12, 0, 0, 0, 0)],
    ["2019/9/12 midnight + 30 min", 3, dt(2019, 9, 12, 0, 30, 0, 0)],
    ["tomorrow", 0, dt(2019, 9, 2, 0, 0, 0, 0)],
    ["tomorrow 9:23:00", 0, dt(2019, 9, 2, 9, 23, 0, 0)],
    ["tomorrow 9:23", 0, dt(2019, 9, 2, 9, 23, 0, 0)],
    ["tomorrow noon", 0, dt(2019, 9, 2, 12, 0, 0, 0)],
    ["today", 0, dt(2019, 9, 1, 0, 0, 0, 0)],
    ["sunday", 0, dt(2019, 9, 1, 0, 0, 0, 0)],
    ["monday+2.5 hours", 0, dt(2019, 9, 2, 2, 30, 0, 0)],
    ["monday + 1 day", 0, dt(2019, 9, 3, 0, 0, 0, 0)],
    ["monday + 1 week", 0, dt(2019, 9, 9, 0, 0, 0, 0)],
    ["tuesday", 0, dt(2019, 9, 3, 0, 0, 0, 0)],
    ["wednesday", 0, dt(2019, 9, 4, 0, 0, 0, 0)],
    ["thursday", 0, dt(2019, 9, 5, 0, 0, 0, 0)],
    ["thursday 00:00", 0, dt(2019, 9, 5, 0, 0, 0, 0)],
    ["thursday 0:0:0", 0, dt(2019, 9, 5, 0, 0, 0, 0)],
    ["friday", 0, dt(2019, 9, 6, 0, 0, 0, 0)],
    ["saturday", 0, dt(2019, 9, 7, 0, 0, 0, 0)],
    ["sun", 0, dt(2019, 9, 1, 0, 0, 0, 0)],
    ["mon", 0, dt(2019, 9, 2, 0, 0, 0, 0)],
    ["tue", 0, dt(2019, 9, 3, 0, 0, 0, 0)],
    ["wed 9:45 + 42 sec", 0, dt(2019, 9, 4, 9, 45, 42, 0)],
    ["thu", 0, dt(2019, 9, 5, 0, 0, 0, 0)],
    ["fri 16:11:15.5", 0, dt(2019, 9, 6, 16, 11, 15, 500000)],
    ["sat", 0, dt(2019, 9, 7, 0, 0, 0, 0)],
    ["14:56", 0, dt(2019, 9, 1, 14, 56, 0, 0)],
    ["8:00", 0, dt(2019, 9, 1, 8, 0, 0, 0)],
    ["16:01", 0, dt(2019, 9, 1, 16, 1, 0, 0)],
    ["14:56", 1, dt(2019, 9, 2, 14, 56, 0, 0)],
    ["8:00:23.6", 1, dt(2019, 9, 2, 8, 0, 23, 600000)],
    ["sunrise", 0, dt(2019, 9, 1, 6, 37, 58, 0)],
    ["sunrise", 1, dt(2019, 9, 2, 6, 38, 49, 0)],
    ["sunrise", 2, dt(2019, 9, 3, 6, 39, 41, 0)],
    ["tuesday sunrise", 0, dt(2019, 9, 3, 6, 39, 41, 0)],
    ["sunrise + 1hr", 0, dt(2019, 9, 1, 7, 37, 58, 0)],
    ["sunset", 0, dt(2019, 9, 1, 19, 37, 23, 0)],
    ["now", 0, dt(2019, 9, 1, 13, 0, 0, 0)],
    ["now +1 min", 0, dt(2019, 9, 1, 13, 1, 0, 0)],
    ["now +1 hours", 0, dt(2019, 9, 1, 14, 0, 0, 0)],
    ["2019/11/4 sunset + 1min", 0, dt(2019, 11, 4, 17, 6, 37, 0)],
    ["11/4 sunset + 2min", 0, dt(2019, 11, 4, 17, 7, 37, 0)],
    ["+5 min", 0, dt(2019, 9, 1, 0, 5, 0, 0)],
]


@pytest.mark.asyncio
async def test_parse_date_time(hass, caplog):
    """Run time parse datetime tests."""

    #
    # Hardcode a location and timezone so we can check sunrise
    # and sunset.
    #
    hass.config.latitude = 38
    hass.config.longitude = -122
    hass.config.elevation = 0
    hass.config.time_zone = "America/Los_Angeles"

    Function.init(hass)
    TrigTime.init(hass)

    #
    # This set of tests assumes it's currently 13:00 on 2019/9/1
    #
    now = dt(2019, 9, 1, 13, 0, 0, 0)

    with (
        patch("homeassistant.util.dt.utcnow", return_value=now),
    ):
        for test_data in parseDateTimeTests:
            spec, date_offset, expect = test_data
            out, _ = await TrigTime.parse_date_time(spec, date_offset, now, now)
            assert out == expect
    await Function.waiter_sync()
    await Function.waiter_stop()
    await Function.reaper_stop()


parseDateTimeTestsDayNames = [
    ["thu", 0, dt(2019, 9, 5, 0, 0, 0, 0)],
    ["fri noon", 0, dt(2019, 9, 6, 12, 0, 0, 0)],
    ["sunday", 0, dt(2019, 9, 8, 0, 0, 0, 0)],
    ["monday", 0, dt(2019, 9, 9, 0, 0, 0, 0)],
]


@pytest.mark.asyncio
async def test_parse_date_time_day_names(hass, caplog):
    """Run time parse datetime on day of week names."""
    #
    # Hardcode a location and timezone so we can check sunrise
    # and sunset.
    #
    hass.config.latitude = 38
    hass.config.longitude = -122
    hass.config.elevation = 0
    hass.config.time_zone = "America/Los_Angeles"

    Function.init(hass)
    TrigTime.init(hass)

    #
    # This set of tests assumes it's currently 13:00 on 2019/9/3
    #
    now = dt(2019, 9, 3, 13, 0, 0, 0)
    with (
        patch("homeassistant.util.dt.utcnow", return_value=now),
    ):
        for test_data in parseDateTimeTestsDayNames:
            spec, date_offset, expect = test_data
            out, _ = await TrigTime.parse_date_time(spec, date_offset, now, now)
            assert out == expect
    await Function.waiter_sync()
    await Function.waiter_stop()
    await Function.reaper_stop()


@pytest.mark.parametrize(
    "spec,now,expected",
    [
        (
            ["range(1:00, 4:00)", "not range(2:00, 3:00)", "range(22:00, 0:00)", "not range(3:30, 3:45)"],
            dt(2019, 8, 31, 22, 0, 0, 0),
            True,
        ),
        ("range(2019/9/1 8:00, 2019/9/1 18:00)", dt(2019, 8, 31, 8, 0, 0, 0), False),
        ("range(2019/9/1 8:00, 2019/9/1 18:00)", dt(2019, 9, 1, 7, 59, 59, 0), False),
        ("range(2019/9/1 8:00, 2019/9/1 18:00)", dt(2019, 9, 1, 8, 0, 0, 0), True),
        ("range(2019/9/1 8:00, 2019/9/1 18:00)", dt(2019, 9, 1, 18, 0, 0, 0), True),
        ("range(2019/9/1 8:00, 2019/9/1 18:00)", dt(2019, 9, 1, 18, 0, 0, 1), False),
        ("range(2019/9/1 8:00, 2019/9/3  6:00)", dt(2019, 8, 31, 8, 0, 0, 0), False),
        ("range(2019/9/1 8:00, 2019/9/3  6:00)", dt(2019, 9, 1, 7, 59, 59, 0), False),
        ("range(2019/9/1 8:00, 2019/9/3  6:00)", dt(2019, 9, 1, 8, 0, 0, 0), True),
        ("range(2019/9/1 8:00, 2019/9/3  6:00)", dt(2019, 9, 3, 6, 0, 0, 0), True),
        ("range(2019/9/1 8:00, 2019/9/3  6:00)", dt(2019, 9, 3, 6, 0, 0, 1), False),
        ("range(now, now)", dt(2019, 9, 1, 12, 59, 59, 999999), False),
        ("range(now, now)", dt(2019, 9, 1, 13, 0, 0, 0), True),
        ("range(now, now)", dt(2019, 9, 1, 13, 0, 0, 1), False),
        ("range(now + 1min, now + 1hour)", dt(2019, 9, 1, 13, 0, 59, 999999), False),
        ("range(now + 1min, now + 1hour)", dt(2019, 9, 1, 13, 1, 0, 0), True),
        ("range(now + 1min, now + 1hour)", dt(2019, 9, 1, 14, 0, 0, 0), True),
        ("range(now + 1min, now + 1hour)", dt(2019, 9, 1, 14, 0, 0, 1), False),
        ("range(10:00, 20:00)", dt(2019, 9, 3, 9, 59, 59, 999999), False),
        ("range(10:00, 20:00)", dt(2019, 9, 3, 10, 0, 0, 0), True),
        ("range(10:00, 20:00)", dt(2019, 9, 3, 20, 0, 0, 0), True),
        ("range(10:00, 20:00)", dt(2019, 9, 3, 20, 0, 0, 1), False),
        ("range(20:00, 10:00)", dt(2019, 9, 3, 9, 59, 59, 999999), True),
        ("range(20:00, 10:00)", dt(2019, 9, 3, 10, 0, 0, 0), True),
        ("range(20:00, 10:00)", dt(2019, 9, 3, 10, 0, 0, 1), False),
        ("range(20:00, 10:00)", dt(2019, 9, 3, 9, 59, 59, 999999), True),
        ("range(20:00, 10:00)", dt(2019, 9, 3, 20, 0, 0, 1), True),
        ("not range(20:00, 10:00)", dt(2019, 9, 3, 10, 0, 0, 0), False),
        ("not range(20:00, 10:00)", dt(2019, 9, 3, 9, 59, 59, 999999), False),
        ("not range(20:00, 10:00)", dt(2019, 9, 3, 20, 0, 0, 0), False),
        ("not range(20:00, 10:00)", dt(2019, 9, 3, 19, 59, 59, 999999), True),
        ("not range(20:00, 10:00)", dt(2019, 9, 3, 12, 0, 0, 0), True),
        ("not range(20:00, 10:00)", dt(2019, 9, 3, 0, 0, 0, 0), False),
        ("range(sunrise, sunset)", dt(2019, 9, 1, 6, 37, 57, 0), False),
        ("range(sunrise, sunset)", dt(2019, 9, 1, 6, 37, 59, 0), True),
        ("range(sunrise, sunset - 20m)", dt(2019, 9, 1, 19, 17, 22, 0), True),
        ("range(sunrise, sunset - 20m)", dt(2019, 9, 1, 19, 17, 24, 0), False),
        ("range(sunrise + 20m, sunset)", dt(2019, 9, 2, 6, 58, 48, 0), False),
        ("range(sunrise + 20m, sunset)", dt(2019, 9, 2, 6, 58, 50, 0), True),
        ("range(sunrise, sunset + 1m)", dt(2019, 11, 4, 17, 6, 36, 0), True),
        ("range(sunrise, sunset + 1m)", dt(2019, 11, 4, 17, 6, 38, 0), False),
        ("cron(* * * * *)", dt(2019, 9, 3, 6, 0, 0, 0), True),
        ("cron(* * * 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), True),
        ("cron(* * 3 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), True),
        ("cron(* 6 3 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), True),
        ("cron(0 6 3 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), True),
        ("cron(* * 4 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), False),
        ("not cron(0 6 3 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), False),
        ("not cron(* * 4 9 *)", dt(2019, 9, 3, 6, 0, 0, 0), True),
    ],
    ids=lambda x: x if not isinstance(x, (dt, list)) else str(x),
)
@pytest.mark.asyncio
async def test_timer_active_check(hass, spec, now, expected):
    """Run time active check tests."""

    #
    # Hardcode a location and timezone so we can check sunrise
    # and sunset.
    #
    hass.config.latitude = 38
    hass.config.longitude = -122
    hass.config.elevation = 0
    hass.config.time_zone = "America/Los_Angeles"

    startup_time = dt(2019, 9, 1, 13, 0, 0, 0)
    Function.init(hass)
    TrigTime.init(hass)
    # print(f"calling timer_active_check({spec}, {now}, {startup_time})")
    out = await TrigTime.timer_active_check(spec, now, startup_time)
    assert out == expected
    await Function.waiter_sync()
    await Function.waiter_stop()
    await Function.reaper_stop()


timerTriggerNextTests = [
    [["once(2019/9/1 8:00)"], [None]],
    [["once(2019/9/1 15:00)"], [dt(2019, 9, 1, 15, 0, 0, 0)]],
    [["once(15:00)"], [dt(2019, 9, 1, 15, 0, 0, 0)]],
    [["once(15:00 + 2d)"], [dt(2019, 9, 1, 15, 0, 0, 0), dt(2019, 9, 2, 15, 0, 0, 0)]],
    [["once(15:00 - 48h)"], [dt(2019, 9, 1, 15, 0, 0, 0), dt(2019, 9, 2, 15, 0, 0, 0)]],
    [["once(11:00 + 2d)"], [dt(2019, 9, 2, 11, 0, 0, 0), dt(2019, 9, 3, 11, 0, 0, 0)]],
    [["once(11:00 - 48h)"], [dt(2019, 9, 2, 11, 0, 0, 0), dt(2019, 9, 3, 11, 0, 0, 0)]],
    [["once(13:00:0.09)"], [dt(2019, 9, 2, 13, 0, 0, 90000)]],
    [["once(9:00)"], [dt(2019, 9, 2, 9, 0, 0, 0)]],
    [["once(wed 9:00)"], [dt(2019, 9, 4, 9, 0, 0, 0)]],
    [["once(2019/9/10 23:59:13)"], [dt(2019, 9, 10, 23, 59, 13, 0)]],
    [["once(now)"], [dt(2019, 9, 1, 13, 0, 0, 100000), None]],
    [["once(now + 1min)"], [dt(2019, 9, 1, 13, 1, 0, 100000), None]],
    [["once(now + 1day)"], [dt(2019, 9, 2, 13, 0, 0, 100000), None]],
    [
        ["period(2019/9/1 13:00, 120s)"],
        [dt(2019, 9, 1, 13, 2, 0, 0), dt(2019, 9, 1, 13, 4, 0, 0), dt(2019, 9, 1, 13, 6, 0, 0)],
    ],
    [
        ["period(13:01, 120s)"],
        [dt(2019, 9, 1, 13, 1, 0, 0), dt(2019, 9, 1, 13, 3, 0, 0), dt(2019, 9, 1, 13, 5, 0, 0)],
    ],
    [
        ["period(10:01, 120s, 12:00)"],
        [dt(2019, 9, 2, 10, 1, 0, 0), dt(2019, 9, 2, 10, 3, 0, 0), dt(2019, 9, 2, 10, 5, 0, 0)],
    ],
    [["period(2019/9/1 12:59, 180s)"], [dt(2019, 9, 1, 13, 2, 0, 0)]],
    [["period(2019/9/1 12:50, 180s)"], [dt(2019, 9, 1, 13, 2, 0, 0)]],
    [
        ["period(2019/9/1 0:50, 180s)"],
        [
            dt(2019, 9, 1, 13, 2, 0, 0),
            dt(2019, 9, 1, 13, 5, 0, 0),
            dt(2019, 9, 1, 13, 8, 0, 0),
            dt(2019, 9, 1, 13, 11, 0, 0),
        ],
    ],
    [
        ["period(2019/9/1 13:00, 120s, 2019/9/1 13:04)"],
        [dt(2019, 9, 1, 13, 2, 0, 0), dt(2019, 9, 1, 13, 4, 0, 0), None],
    ],
    [
        ["period(18:00, 4 hr, 6:00)"],
        [
            dt(2019, 9, 1, 18, 0, 0, 0),
            dt(2019, 9, 1, 22, 0, 0, 0),
            dt(2019, 9, 2, 2, 0, 0, 0),
            dt(2019, 9, 2, 6, 0, 0, 0),
            dt(2019, 9, 2, 18, 0, 0, 0),
            dt(2019, 9, 2, 22, 0, 0, 0),
            dt(2019, 9, 3, 2, 0, 0, 0),
            dt(2019, 9, 3, 6, 0, 0, 0),
            dt(2019, 9, 3, 18, 0, 0, 0),
        ],
    ],
    [
        ["period(18:00, 12 hr, 6:00)"],
        [
            dt(2019, 9, 1, 18, 0, 0, 0),
            dt(2019, 9, 2, 6, 0, 0, 0),
            dt(2019, 9, 2, 18, 0, 0, 0),
            dt(2019, 9, 3, 6, 0, 0, 0),
        ],
    ],
    [
        ["period(18:00, 12.0001 hr, 6:00)"],
        [
            dt(2019, 9, 1, 18, 0, 0, 0),
            dt(2019, 9, 2, 18, 0, 0, 0),
            dt(2019, 9, 3, 18, 0, 0, 0),
            dt(2019, 9, 4, 18, 0, 0, 0),
        ],
    ],
    [
        ["period(6:00, 12 hr, 18:00)"],
        [
            dt(2019, 9, 1, 18, 0, 0, 0),
            dt(2019, 9, 2, 6, 0, 0, 0),
            dt(2019, 9, 2, 18, 0, 0, 0),
            dt(2019, 9, 3, 6, 0, 0, 0),
            dt(2019, 9, 3, 18, 0, 0, 0),
            dt(2019, 9, 4, 6, 0, 0, 0),
        ],
    ],
    [
        ["period(6:00, 12.0001 hr, 18:00)"],
        [dt(2019, 9, 2, 6, 0, 0, 0), dt(2019, 9, 3, 6, 0, 0, 0), dt(2019, 9, 4, 6, 0, 0, 0)],
    ],
    [
        ["period(sunset, 4 hours, sunrise)"],
        [
            dt(2019, 9, 1, 19, 37, 23),
            dt(2019, 9, 1, 23, 37, 23),
            dt(2019, 9, 2, 3, 37, 23),
            dt(2019, 9, 2, 19, 35, 53),
            dt(2019, 9, 2, 23, 35, 53),
            dt(2019, 9, 3, 3, 35, 53),
            dt(2019, 9, 3, 19, 34, 23),
            dt(2019, 9, 3, 23, 34, 23),
        ],
    ],
    [
        ["period(11/3 0:01, 1 hr)"],
        [
            dt(2019, 11, 3, 0, 1, 0, 0),
            dt(2019, 11, 3, 1, 1, 0, 0),
            dt(2019, 11, 3, 2, 1, 0, 0),
            dt(2019, 11, 3, 3, 1, 0, 0),
            dt(2019, 11, 3, 4, 1, 0, 0),
        ],
    ],
    [
        ["period(11/3 0:01, 1 day)"],
        [
            dt(2019, 11, 3, 0, 1, 0, 0),
            dt(2019, 11, 4, 0, 1, 0, 0),
            dt(2019, 11, 5, 0, 1, 0, 0),
            dt(2019, 11, 6, 0, 1, 0, 0),
            dt(2019, 11, 7, 0, 1, 0, 0),
        ],
    ],
    [
        ["period(now, 1 day)"],
        [
            dt(2019, 9, 1, 13, 0, 0, 100000),
            dt(2019, 9, 2, 13, 0, 0, 100000),
            dt(2019, 9, 3, 13, 0, 0, 100000),
        ],
    ],
    [
        ["period(now +1 hours, 1 hours, now+4 hours)"],
        [
            dt(2019, 9, 1, 14, 0, 0, 100000),
            dt(2019, 9, 1, 15, 0, 0, 100000),
            dt(2019, 9, 1, 16, 0, 0, 100000),
            dt(2019, 9, 1, 17, 0, 0, 100000),
            None,
        ],
    ],
    # see #714 for these two cases - in 1.6.4 and prior, they keep triggering since the
    # end time is considered tomorrow
    [
        ["period(now, 1 hours, 15:00.1)"],
        [
            dt(2019, 9, 1, 13, 0, 0, 100000),
            dt(2019, 9, 1, 14, 0, 0, 100000),
            dt(2019, 9, 1, 15, 0, 0, 100000),
            None,
        ],
    ],
    [
        ["period(now, 1 hours, 10:00)"],
        [
            None,
        ],
    ],
    [
        ["period(now, 1 hours, today 15:01)"],
        [
            dt(2019, 9, 1, 13, 0, 0, 100000),
            dt(2019, 9, 1, 14, 0, 0, 100000),
            dt(2019, 9, 1, 15, 0, 0, 100000),
            None,
        ],
    ],
    [
        ["period(now, 1 hours, 10:00)"],
        [
            None,
        ],
    ],
    [
        ["period(today 11:00, 1 hours, today 10:00)"],
        [
            None,
        ],
    ],
    [
        ["cron(0 14 * * *)"],
        [
            dt(2019, 9, 1, 14, 0, 0, 0),
            dt(2019, 9, 2, 14, 0, 0, 0),
            dt(2019, 9, 3, 14, 0, 0, 0),
            dt(2019, 9, 4, 14, 0, 0, 0),
        ],
    ],
    [
        ["cron(0 14 10-13 * *)"],
        [
            dt(2019, 9, 10, 14, 0, 0, 0),
            dt(2019, 9, 11, 14, 0, 0, 0),
            dt(2019, 9, 12, 14, 0, 0, 0),
            dt(2019, 9, 13, 14, 0, 0, 0),
            dt(2019, 10, 10, 14, 0, 0, 0),
            dt(2019, 10, 11, 14, 0, 0, 0),
            dt(2019, 10, 12, 14, 0, 0, 0),
            dt(2019, 10, 13, 14, 0, 0, 0),
            dt(2019, 11, 10, 14, 0, 0, 0),
        ],
    ],
    [
        ["cron(0 14 10,11-12,13 * *)"],
        [
            dt(2019, 9, 10, 14, 0, 0, 0),
            dt(2019, 9, 11, 14, 0, 0, 0),
            dt(2019, 9, 12, 14, 0, 0, 0),
            dt(2019, 9, 13, 14, 0, 0, 0),
            dt(2019, 10, 10, 14, 0, 0, 0),
            dt(2019, 10, 11, 14, 0, 0, 0),
            dt(2019, 10, 12, 14, 0, 0, 0),
            dt(2019, 10, 13, 14, 0, 0, 0),
            dt(2019, 11, 10, 14, 0, 0, 0),
        ],
    ],
    [
        ["cron(23 8 * * 2,4-5)"],
        [
            dt(2019, 9, 3, 8, 23, 0, 0),
            dt(2019, 9, 5, 8, 23, 0, 0),
            dt(2019, 9, 6, 8, 23, 0, 0),
            dt(2019, 9, 10, 8, 23, 0, 0),
            dt(2019, 9, 12, 8, 23, 0, 0),
        ],
    ],
    [
        ["cron(23 8 3-4 * 5-6)"],
        [
            dt(2019, 9, 3, 8, 23, 0, 0),
            dt(2019, 9, 4, 8, 23, 0, 0),
            dt(2019, 9, 6, 8, 23, 0, 0),
            dt(2019, 9, 7, 8, 23, 0, 0),
            dt(2019, 9, 13, 8, 23, 0, 0),
            dt(2019, 9, 14, 8, 23, 0, 0),
        ],
    ],
    [
        # test "/n"
        ["cron(*/10 14 * * *)"],
        [
            dt(2019, 9, 1, 14, 0, 0, 0),
            dt(2019, 9, 1, 14, 10, 0, 0),
            dt(2019, 9, 1, 14, 20, 0, 0),
            dt(2019, 9, 1, 14, 30, 0, 0),
            dt(2019, 9, 1, 14, 40, 0, 0),
            dt(2019, 9, 1, 14, 50, 0, 0),
            dt(2019, 9, 2, 14, 0, 0, 0),
            dt(2019, 9, 2, 14, 10, 0, 0),
        ],
    ],
    [
        # test "/n" spanning 2 hours
        ["cron(*/30 14-15 * * *)"],
        [
            dt(2019, 9, 1, 14, 0, 0, 0),
            dt(2019, 9, 1, 14, 30, 0, 0),
            dt(2019, 9, 1, 15, 0, 0, 0),
            dt(2019, 9, 1, 15, 30, 0, 0),
            dt(2019, 9, 2, 14, 0, 0, 0),
            dt(2019, 9, 2, 14, 30, 0, 0),
        ],
    ],
    [
        # test optional 6th argument seconds
        ["cron(0 14 * * * 10,35)"],
        [
            dt(2019, 9, 1, 14, 0, 10, 0),
            dt(2019, 9, 1, 14, 0, 35, 0),
            dt(2019, 9, 2, 14, 0, 10, 0),
            dt(2019, 9, 2, 14, 0, 35, 0),
        ],
    ],
    [
        # invalid cron expression returns None
        ["cron(0 14 1-2-3 x *)"],
        [None],
    ],
]


@pytest.mark.asyncio
async def test_timer_trigger_next(hass):
    """Run trigger next tests."""
    #
    # Hardcode a location and timezone so we can check sunrise
    # and sunset.
    #
    hass.config.latitude = 38
    hass.config.longitude = -122
    hass.config.elevation = 0
    hass.config.time_zone = "America/Los_Angeles"

    Function.init(hass)
    TrigTime.init(hass)

    for test_data in timerTriggerNextTests:
        startup_time = now = dt(2019, 9, 1, 13, 0, 0, 100000)
        spec, expect_seq = test_data
        for expect in expect_seq:
            t_next, _ = await TrigTime.timer_trigger_next(spec, now, startup_time)
            assert t_next == expect
            if t_next is None:
                break
            now = t_next + timedelta(microseconds=1)
    await Function.waiter_sync()
    await Function.waiter_stop()
    await Function.reaper_stop()


timerTriggerNextTestsMonthRollover = [
    [
        # 1pm every day
        "cron(0 13 * * *)",
        [dt(2020, 7, 1, 13, 0, 0, 0), dt(2020, 7, 2, 13, 0, 0, 0), dt(2020, 7, 3, 13, 0, 0, 0)],
    ],
    [
        # 1pm on 4th, 5th, 6th of each month
        "cron(0 13 4-6 * *)",
        [
            dt(2020, 7, 4, 13, 0, 0, 0),
            dt(2020, 7, 5, 13, 0, 0, 0),
            dt(2020, 7, 6, 13, 0, 0, 0),
            dt(2020, 8, 4, 13, 0, 0, 0),
            dt(2020, 8, 5, 13, 0, 0, 0),
        ],
    ],
    [
        # 1pm on 10th of month except nov
        "cron(0 13 10 1-10,12 *)",
        [
            dt(2020, 7, 10, 13, 0, 0, 0),
            dt(2020, 8, 10, 13, 0, 0, 0),
            dt(2020, 9, 10, 13, 0, 0, 0),
            dt(2020, 10, 10, 13, 0, 0, 0),
            dt(2020, 12, 10, 13, 0, 0, 0),
            dt(2021, 1, 10, 13, 0, 0, 0),
            dt(2021, 2, 10, 13, 0, 0, 0),
            dt(2021, 3, 10, 13, 0, 0, 0),
        ],
    ],
    [
        # 1pm on monday
        ["cron(0 13 * * 1)"],
        [
            dt(2020, 7, 6, 13, 0, 0, 0),
            dt(2020, 7, 13, 13, 0, 0, 0),
            dt(2020, 7, 20, 13, 0, 0, 0),
            dt(2020, 7, 27, 13, 0, 0, 0),
            dt(2020, 8, 3, 13, 0, 0, 0),
        ],
    ],
    [
        # 1pm on monday, or 28th
        ["cron(0 13 28 * 1)"],
        [
            dt(2020, 7, 6, 13, 0, 0, 0),
            dt(2020, 7, 13, 13, 0, 0, 0),
            dt(2020, 7, 20, 13, 0, 0, 0),
            dt(2020, 7, 27, 13, 0, 0, 0),
            dt(2020, 7, 28, 13, 0, 0, 0),
            dt(2020, 8, 3, 13, 0, 0, 0),
        ],
    ],
    [
        # 1pm on sunday and tuesday in feb & dec
        "cron(0 13 1 2,12 0,2)",
        [
            dt(2020, 12, 1, 13, 0, 0, 0),
            dt(2020, 12, 6, 13, 0, 0, 0),
            dt(2020, 12, 8, 13, 0, 0, 0),
            dt(2020, 12, 13, 13, 0, 0, 0),
            dt(2020, 12, 15, 13, 0, 0, 0),
            dt(2020, 12, 20, 13, 0, 0, 0),
            dt(2020, 12, 22, 13, 0, 0, 0),
            dt(2020, 12, 27, 13, 0, 0, 0),
            dt(2020, 12, 29, 13, 0, 0, 0),
            dt(2021, 2, 1, 13, 0, 0, 0),
            dt(2021, 2, 2, 13, 0, 0, 0),
            dt(2021, 2, 7, 13, 0, 0, 0),
            dt(2021, 2, 9, 13, 0, 0, 0),
            dt(2021, 2, 14, 13, 0, 0, 0),
        ],
    ],
    [
        # 1pm on 29th of Jan & Feb (only leap years)
        "cron(0 13 29 1,2 *)",
        [
            dt(2021, 1, 29, 13, 0, 0, 0),
            dt(2022, 1, 29, 13, 0, 0, 0),
            dt(2023, 1, 29, 13, 0, 0, 0),
            dt(2024, 1, 29, 13, 0, 0, 0),
            dt(2024, 2, 29, 13, 0, 0, 0),
            dt(2025, 1, 29, 13, 0, 0, 0),
            dt(2026, 1, 29, 13, 0, 0, 0),
        ],
    ],
    [
        # 1pm on 33rd of Jan & Feb -> no such time
        "cron(0 13 33 1,2 *)",
        [None],
    ],
]


@pytest.mark.asyncio
async def test_timer_trigger_next_month_rollover(hass):
    """Run month rollover tests."""

    Function.init(hass)
    TrigTime.init(hass)

    for test_data in timerTriggerNextTestsMonthRollover:
        startup_time = now = dt(2020, 6, 30, 13, 0, 0, 100000)
        spec, expect_seq = test_data
        for expect in expect_seq:
            t_next, _ = await TrigTime.timer_trigger_next(spec, now, startup_time)
            assert t_next == expect
            if t_next is None:
                break
            now = t_next + timedelta(microseconds=1)
    await Function.waiter_sync()
    await Function.waiter_stop()
    await Function.reaper_stop()


timerTriggerDSTNextTests = [
    [
        ["cron(0 0 * * *)"],
        [
            [dt(2019, 11, 4, 0, 0, 0, 0), 90000],
            [dt(2019, 11, 5, 0, 0, 0, 0), 86400],
            [dt(2019, 11, 6, 0, 0, 0, 0), 86400],
        ],
    ],
    [
        ["cron(0 * * * *)"],
        [
            [dt(2019, 11, 3, 1, 0, 0, 0), 3600],
            [dt(2019, 11, 3, 2, 0, 0, 0), 7200],
            [dt(2019, 11, 3, 3, 0, 0, 0), 3600],
            [dt(2019, 11, 3, 4, 0, 0, 0), 3600],
        ],
    ],
    [
        ["cron(1 * * * *)"],
        [
            [dt(2019, 11, 3, 0, 1, 0, 0), 60],
            [dt(2019, 11, 3, 1, 1, 0, 0), 3600],
            [dt(2019, 11, 3, 2, 1, 0, 0), 7200],
            [dt(2019, 11, 3, 3, 1, 0, 0), 3600],
            [dt(2019, 11, 3, 4, 1, 0, 0), 3600],
        ],
    ],
    [
        ["cron(1 * 8,9,10 3 *)"],
        [
            dt(2020, 3, 8, 0, 1, 0, 0),
            [dt(2020, 3, 8, 1, 1, 0, 0), 3600],
            [dt(2020, 3, 8, 2, 1, 0, 0), 3600],
            [dt(2020, 3, 8, 4, 1, 0, 0), 3600],
            [dt(2020, 3, 8, 5, 1, 0, 0), 3600],
        ],
    ],
]


@pytest.mark.asyncio
async def test_timer_trigger_dst_next(hass):
    """Run trigger next tests."""
    #
    # Hardcode a location and timezone so we can check sunrise
    # and sunset.
    #
    hass.config.latitude = 38
    hass.config.longitude = -122
    hass.config.elevation = 0
    hass.config.time_zone = "America/Los_Angeles"

    Function.init(hass)
    TrigTime.init(hass)

    for test_data in timerTriggerDSTNextTests:
        startup_time = now = dt(2019, 11, 3, 0, 0, 0, 0)
        spec, expect_seq = test_data
        for expect in expect_seq:
            t_next, t_next_adj = await TrigTime.timer_trigger_next(spec, now, startup_time)
            delta = (t_next_adj - now).total_seconds()
            # print(f"calling timer_trigger_next({spec}, {dt_util.as_local(now)}, {startup_time}) -> {dt_util.as_local(t_next)} (delta = {delta})")
            if isinstance(expect, list):
                assert t_next == expect[0]
                assert delta == expect[1]
            else:
                assert t_next == expect
            if t_next is None:
                break
            now = t_next
    await Function.waiter_sync()
    await Function.waiter_stop()
    await Function.reaper_stop()


# #617's expression, as its f-string renders it: lines end in "and " with no brackets around it all
ISSUE_617_EXPR = (
    "\n"
    "sensor.office_state in ['recently occupied', 'unoccupied', 'dormant', 'unavailable'] and \n"
    "(sensor.octoprint_actual_tool0_temp == 'unavailable' or float(sensor.octoprint_actual_tool0_temp) <= 110) and \n"
    "(sensor.octoprint_actual_bed_temp == 'unavailable' or float(sensor.octoprint_actual_bed_temp) <= 110)\n"
)

TRIGGER_EXPR_OK = [
    "pyscript.a == '1'",
    " pyscript.a == '1'",
    "pyscript.a == '1' ",
    "\npyscript.a == '1'\n",
    "\t pyscript.a == '1' \t\r\n",
    ISSUE_617_EXPR,
    "pyscript.a == '1' and\n    pyscript.b == '2'",
    "pyscript.a == '1'  # last line",
    "pyscript.a == '1' and  # middle line\npyscript.b == '2'",
    "\n  pyscript.a == '1' or  # first\n  pyscript.b == '2'  # last\n",
    "x := pyscript.a",
    "pyscript.a == '1' \\",
    "pyscript.a == '1' and \\\npyscript.b == '2'",
    "pyscript.a, pyscript.b",
    "x for x in pyscript.a",
    "()",
    "(pyscript.a == '1')",
    "pyscript.a == ')'",
    "pyscript.a == '1'  # closing )",
    "pyscript.a == 'a) or (b'",
    "pyscript.a == '1'  # a) or (b",
    "f'{pyscript.a})' == 'x)'",
    "pyscript.a == 'é' and\n  pyscript.b == 'ü'",
]


@pytest.fixture
def ast_eval(monkeypatch):
    """Return an AstEval to parse trigger expressions with (parsing needs no running hass)."""
    hass = SimpleNamespace(data={DOMAIN: {CONFIG_ENTRY: MockConfigEntry(domain=DOMAIN, data={})}})
    monkeypatch.setattr(Function, "hass", hass)
    return AstEval("test", global_ctx=GlobalContext("test", global_sym_table={}, manager=GlobalContextMgr))


def cpython_parse(expr):
    """Parse expr the way the trigger code does, with CPython."""
    return ast_module.parse("(" + expr + "\n)", mode="eval")


@pytest.mark.parametrize("expr", TRIGGER_EXPR_OK)
def test_parse_trigger_expr_matches_cpython(ast_eval, expr):
    """An expression parses as CPython parses it inside brackets, and node positions are on the text as written."""
    ast_eval.parse_trigger_expr(expr)
    assert ast_eval.code_str == expr
    assert ast_eval.code_list == expr.split("\n")
    cpython_ast = cpython_parse(expr)
    assert ast_module.dump(ast_eval.ast) == ast_module.dump(cpython_ast)
    for node, cpython_node in zip(ast_module.walk(ast_eval.ast), ast_module.walk(cpython_ast), strict=True):
        if not hasattr(node, "lineno"):
            continue
        segment = ast_module.get_source_segment("(" + expr + "\n)", cpython_node)
        if segment.startswith("(") and segment.endswith(")") and cpython_node.col_offset == 0:
            # a bare tuple or generator expression takes in the added brackets
            assert node.lineno == cpython_node.lineno and node.col_offset == 0
            continue
        assert ast_module.get_source_segment(expr, node) == segment


def test_parse_trigger_expr_list_of_one(ast_eval):
    """A list of one expression is the same as the expression on its own."""
    ast_eval.parse_trigger_expr([ISSUE_617_EXPR])
    assert ast_eval.code_str == ISSUE_617_EXPR
    assert ast_module.dump(ast_eval.ast) == ast_module.dump(cpython_parse(ISSUE_617_EXPR))


def test_parse_trigger_expr_several(ast_eval):
    """Several expressions are each put inside brackets, in an any([...])."""
    exprs = [ISSUE_617_EXPR, " pyscript.a == '1'  # comment", "pyscript.a, pyscript.b"]
    ast_eval.parse_trigger_expr(exprs)
    expected = "any([(" + "\n), (".join(exprs) + "\n)])"
    assert ast_eval.code_str == expected
    cpython_ast = ast_module.parse(expected, mode="eval")
    assert ast_module.dump(ast_eval.ast, include_attributes=True) == ast_module.dump(
        cpython_ast, include_attributes=True
    )
    # the bare tuple is one element of the list
    assert len(ast_eval.ast.body.args[0].elts) == 3


def syntax_error_fields(exc):
    """Return the fields of a SyntaxError that a script can read."""
    return (type(exc), exc.msg, exc.lineno, exc.offset, exc.end_lineno, exc.end_offset, exc.text)


def cpython_error(source, mode="eval"):
    """Return CPython's SyntaxError fields for source."""
    with pytest.raises(SyntaxError) as exc:
        ast_module.parse(source, mode=mode)
    return syntax_error_fields(exc.value)


TRIGGER_EXPR_ERRORS = [
    # empty, blank and comment-only expressions stay errors (a written "()" is fine)
    ("", (SyntaxError, "expression is empty", 1, 1, 1, 2, "")),
    ("   ", (SyntaxError, "expression is empty", 1, 1, 1, 2, "   ")),
    ("\n\t\n", (SyntaxError, "expression is empty", 1, 1, 1, 2, "")),
    ("  # just a comment\n", (SyntaxError, "expression is empty", 1, 1, 1, 2, "  # just a comment")),
    # closing the added bracket before the end isn't one expression
    ("a) or (b", (SyntaxError, "unmatched ')'", 1, 2, 1, 3, "a) or (b")),
    ("pyscript.a == '1')", (SyntaxError, "unmatched ')'", 1, 18, 1, 19, "pyscript.a == '1')")),
    ("\n  a and\n  b] or [c", (SyntaxError, "unmatched ']'", 3, 4, 3, 5, "  b] or [c")),
    # a bracket the expression leaves open
    ("x + (a", (SyntaxError, "'(' was never closed", 1, 5, 1, 6, "x + (a")),
    ("pyscript.a == 1 and\n  [b", (SyntaxError, "'[' was never closed", 2, 3, 2, 4, "  [b")),
    # cut short: the error is at the last character of the last line that isn't blank
    ("x == 1 and", (SyntaxError, "invalid syntax", 1, 10, 1, 11, "x == 1 and")),
    ("\n  x == 1 and  \n\n", (SyntaxError, "invalid syntax", 2, 12, 2, 13, "  x == 1 and  ")),
    # syntax errors on the first line move back by one; later lines keep their place
    ("a b", (SyntaxError, "invalid syntax. Perhaps you forgot a comma?", 1, 1, 1, 4, "a b")),
    (
        " pyscript.a = 1",
        (
            SyntaxError,
            "cannot assign to attribute here. Maybe you meant '==' instead of '='?",
            1,
            2,
            1,
            12,
            " pyscript.a = 1",
        ),
    ),
    (
        "pyscript.a == 1 and\n  (b c)",
        (SyntaxError, "invalid syntax. Perhaps you forgot a comma?", 2, 4, 2, 7, "  (b c)"),
    ),
    # CPython's "forgot a comma?" runs from the start of the expression to the problem
    (
        "pyscript.a == 1 and\n  b c",
        (SyntaxError, "invalid syntax. Perhaps you forgot a comma?", 1, 1, 2, 6, "pyscript.a == 1 and"),
    ),
    ("pyscript.a == 1 and\n  (b +\n  * 2)", (SyntaxError, "invalid syntax", 3, 3, 3, 4, "  * 2)")),
]


@pytest.mark.parametrize("expr, expected", TRIGGER_EXPR_ERRORS)
def test_parse_trigger_expr_errors(ast_eval, expr, expected):
    """Syntax errors point at the expression as written, in the fields a script can read."""
    with pytest.raises(SyntaxError) as exc:
        ast_eval.parse_trigger_expr(expr)
    assert syntax_error_fields(exc.value) == expected
    assert exc.value.args == (
        exc.value.msg,
        (exc.value.filename, *expected[2:4], expected[6], *expected[4:6]),
    )
    assert ast_eval.code_str == expr
    assert ast_eval.ast is None


@pytest.mark.parametrize(
    "expr",
    [
        "a b",
        "pyscript.a == 1 and\n  (b c)",
        "pyscript.a == 1 and\n  b c",
        "pyscript.a == 1 and\n  (b +\n  * 2)",
        " pyscript.a = 1",
        "\n  pyscript.a +\n  * 2",
    ],
)
def test_parse_trigger_expr_errors_match_cpython(ast_eval, expr):
    """The message is CPython's inside brackets, one place to the left on the first line."""
    with pytest.raises(SyntaxError) as exc:
        ast_eval.parse_trigger_expr(expr)
    cpython = list(cpython_error("(" + expr + "\n)"))
    if cpython[2] == 1:
        cpython[3] -= 1
        cpython[6] = cpython[6][1:]
    if cpython[4] == 1:
        cpython[5] -= 1
    # the text is the line as written, without the new line CPython sometimes keeps
    cpython[6] = cpython[6].rstrip("\n")
    assert syntax_error_fields(exc.value) == tuple(cpython)


@pytest.mark.parametrize("expr", ["a) or (b", "x + (a", "x + [a", "f(a, (b", "a]"])
def test_parse_trigger_expr_bracket_errors_match_cpython(ast_eval, expr):
    """Bracket errors give the message and place CPython gives for the text on its own."""
    with pytest.raises(SyntaxError) as exc:
        ast_eval.parse_trigger_expr(expr)
    assert syntax_error_fields(exc.value)[:4] == cpython_error(expr)[:4]
    assert exc.value.text == cpython_error(expr)[6]


SEVERAL_ERRORS = [
    # each entry is checked inside its own brackets; positions are in the any([...]) text
    (
        ["pyscript.a == '1'", "b c"],
        (SyntaxError, "invalid syntax. Perhaps you forgot a comma?", 2, 5, 2, 8, "), (b c"),
    ),
    (
        ["pyscript.a == '1'", "b or\n  (c d)"],
        (SyntaxError, "invalid syntax. Perhaps you forgot a comma?", 3, 4, 3, 7, "  (c d)"),
    ),
    (["pyscript.a == '1'", "a) or (b"], (SyntaxError, "unmatched ')'", 2, 6, 2, 7, "), (a) or (b")),
    (["x + (a", "pyscript.a == '1'"], (SyntaxError, "'(' was never closed", 1, 11, 1, 12, "any([(x + (a")),
    (
        ["pyscript.a == '1'", "  # comment"],
        (SyntaxError, "expression is empty", 2, 4, 2, 5, "), (  # comment"),
    ),
    (["pyscript.a == '1'", "b and"], (SyntaxError, "invalid syntax", 3, 1, 3, 2, ")])")),
]


@pytest.mark.parametrize("exprs, expected", SEVERAL_ERRORS)
def test_parse_trigger_expr_several_errors(ast_eval, exprs, expected):
    """An error in one of several expressions points into the any([...]) text that's shown."""
    with pytest.raises(SyntaxError) as exc:
        ast_eval.parse_trigger_expr(exprs)
    assert syntax_error_fields(exc.value) == expected
    assert ast_eval.code_str.split("\n")[expected[2] - 1] == expected[6]


# the second is written in two parts only to keep the spell checker quiet
@pytest.mark.parametrize("expr", ["b\ré{", "\ré]],}a" + "and{"])
def test_parse_trigger_expr_tokenize_decode_error(ast_eval, expr):
    """Text that makes tokenize fail to decode still gives the parser's SyntaxError, not a codec error."""
    with pytest.raises(SyntaxError) as exc:
        ast_eval.parse_trigger_expr(expr)
    assert not isinstance(exc.value, UnicodeError)
    assert exc.value.msg == cpython_error("(" + expr + "\n)")[1]
    assert ast_eval.ast is None


def test_parse_trigger_expr_script_parse_unchanged(ast_eval):
    """Ordinary parsing keeps Python's rules: no brackets are added."""
    for source in [" 1 + 1", "a and\nb", "1 +"]:
        with pytest.raises(SyntaxError) as exc:
            ast_eval.parse(source, mode="eval")
        assert syntax_error_fields(exc.value) == cpython_error(source)
