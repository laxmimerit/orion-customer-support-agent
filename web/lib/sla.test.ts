import { describe, expect, it } from "vitest";

import { isRunning, lateLabel, slaResult, slaVerdict, toHours } from "@/lib/sla";

type Ticket = Parameters<typeof lateLabel>[0];

// An open ticket with nothing recorded yet, aged inside both targets. Each test changes only what it is about.
function ticket(fields: Partial<Ticket> = {}): Ticket {
  return {
    status: "open",
    first_response_hours: null,
    sla_response_hours: "4.0000",
    resolution_hours: null,
    sla_resolution_hours: "24.0000",
    age_hours: "1.0000",
    ...fields,
  };
}

describe("toHours", () => {
  it("keeps a missing value missing", () => {
    expect(toHours(null)).toBeNull();
  });

  it("reads the API's decimal strings as numbers", () => {
    expect(toHours("7.96")).toBe(7.96);
    expect(toHours("8.0000")).toBe(8);
  });

  it("reads zero as zero, not as missing", () => {
    expect(toHours("0")).toBe(0);
    expect(toHours("0.0000")).toBe(0);
  });
});

describe("slaResult", () => {
  it("is met under the target", () => {
    expect(slaResult(3, 4)).toBe("met");
  });

  it("is met exactly on the target", () => {
    expect(slaResult(4, 4)).toBe("met");
    expect(slaResult(0, 0)).toBe("met");
  });

  it("is missed past the target, however slightly", () => {
    expect(slaResult(5, 4)).toBe("missed");
    expect(slaResult(4.0001, 4)).toBe("missed");
  });

  it("decides nothing with a number missing", () => {
    expect(slaResult(null, 4)).toBeNull();
    expect(slaResult(4, null)).toBeNull();
    expect(slaResult(null, null)).toBeNull();
  });

  it("treats zero as a number, not as missing", () => {
    expect(slaResult(0, 4)).toBe("met");
    expect(slaResult(0.5, 0)).toBe("missed");
  });
});

describe("slaVerdict", () => {
  it("rounds a gap of exactly half a minute up, though the subtraction falls just short", () => {
    expect(slaVerdict(8.075, 8)).toBe("5m late");
    expect(slaVerdict(24.075, 24)).toBe("5m late");
  });

  it("gives no verdict with a number missing", () => {
    expect(slaVerdict(null, 8)).toBeNull();
    expect(slaVerdict(8, null)).toBeNull();
    expect(slaVerdict(null, null)).toBeNull();
  });

  it("says on target when the two are equal", () => {
    expect(slaVerdict(8, 8)).toBe("On target");
    expect(slaVerdict(0, 0)).toBe("On target");
    expect(slaVerdict(toHours("8.0000"), toHours("8"))).toBe("On target");
  });

  it("says how late a missed stage was", () => {
    expect(slaVerdict(10, 8)).toBe("2h late");
    expect(slaVerdict(9.5, 8)).toBe("1h 30m late");
    expect(slaVerdict(8.5, 8)).toBe("30m late");
    expect(slaVerdict(15.96, 8)).toBe("7h 58m late");
  });

  it("says how far inside a met stage was", () => {
    expect(slaVerdict(6, 8)).toBe("2h inside target");
    expect(slaVerdict(6.75, 8)).toBe("1h 15m inside target");
    expect(slaVerdict(7.5, 8)).toBe("30m inside target");
    expect(slaVerdict(7.96, 8)).toBe("2m inside target");
  });

  it("treats zero as a number on either side", () => {
    expect(slaVerdict(0, 4)).toBe("4h inside target");
    expect(slaVerdict(0.5, 0)).toBe("30m late");
  });

  it("says under 1m when the gap rounds to no minutes, never 0m", () => {
    expect(slaVerdict(8.001, 8)).toBe("Under 1m late");
    expect(slaVerdict(7.999, 8)).toBe("Under 1m inside target");
  });

  it("rounds the gap to the nearest minute", () => {
    expect(slaVerdict(8.0083, 8)).toBe("Under 1m late");
    expect(slaVerdict(8.0084, 8)).toBe("1m late");
    expect(slaVerdict(9.9999, 8)).toBe("2h late");
  });
});

describe("isRunning", () => {
  it("runs for a recorded status other than resolved", () => {
    expect(isRunning("open")).toBe(true);
    expect(isRunning("in progress")).toBe(true);
    expect(isRunning("pending")).toBe(true);
  });

  it("stops for a resolved ticket", () => {
    expect(isRunning("resolved")).toBe(false);
  });

  it("does not run with no status recorded", () => {
    expect(isRunning(null)).toBe(false);
  });
});

describe("lateLabel", () => {
  describe("with both times recorded", () => {
    const recorded = { status: "resolved", age_hours: "100.0000" };

    it("is null when both stages are inside their targets", () => {
      expect(lateLabel(ticket({ ...recorded, first_response_hours: "3.0000", resolution_hours: "20.0000" }))).toBeNull();
    });

    it("is null when both stages land exactly on their targets", () => {
      expect(lateLabel(ticket({ ...recorded, first_response_hours: "4.0000", resolution_hours: "24.0000" }))).toBeNull();
    });

    it("names the reply alone", () => {
      expect(lateLabel(ticket({ ...recorded, first_response_hours: "4.0001", resolution_hours: "20.0000" }))).toBe("Reply late");
    });

    it("names the resolution alone", () => {
      expect(lateLabel(ticket({ ...recorded, first_response_hours: "3.0000", resolution_hours: "24.0001" }))).toBe("Resolution late");
    });

    it("names both", () => {
      expect(lateLabel(ticket({ ...recorded, first_response_hours: "5.0000", resolution_hours: "30.0000" }))).toBe("Reply and resolution late");
    });
  });

  describe("with a stage still waiting on a running ticket", () => {
    it("is null while the age is inside both targets", () => {
      expect(lateLabel(ticket())).toBeNull();
    });

    it("is null when the age is exactly on the target", () => {
      expect(lateLabel(ticket({ age_hours: "4.0000" }))).toBeNull();
    });

    it("judges the reply on the ticket's age", () => {
      expect(lateLabel(ticket({ age_hours: "4.0001" }))).toBe("Reply late");
    });

    it("judges both stages on the ticket's age", () => {
      expect(lateLabel(ticket({ age_hours: "24.0001" }))).toBe("Reply and resolution late");
    });

    it("judges only the stage still waiting", () => {
      expect(lateLabel(ticket({ first_response_hours: "2.0000", age_hours: "30.0000" }))).toBe("Resolution late");
    });

    it("keeps a late reply late after the ticket's resolution is on time", () => {
      expect(lateLabel(ticket({ first_response_hours: "5.0000", resolution_hours: "6.0000", age_hours: "30.0000" }))).toBe("Reply late");
    });

    it("is not late with no age recorded", () => {
      expect(lateLabel(ticket({ age_hours: null }))).toBeNull();
    });
  });

  describe("with a recorded time on a running ticket", () => {
    it("uses the recorded time, not the age", () => {
      expect(lateLabel(ticket({ first_response_hours: "1.0000", resolution_hours: "2.0000", age_hours: "100.0000" }))).toBeNull();
    });

    it("counts a recorded zero as a time, not as still waiting", () => {
      expect(lateLabel(ticket({ first_response_hours: "0.0000", resolution_hours: "0.0000", age_hours: "100.0000" }))).toBeNull();
    });
  });

  describe("with a gap in the record", () => {
    it("never marks a resolved ticket late for a missing time", () => {
      expect(lateLabel(ticket({ status: "resolved", age_hours: "100.0000" }))).toBeNull();
    });

    it("still marks the stage that was recorded late on a resolved ticket", () => {
      expect(lateLabel(ticket({ status: "resolved", first_response_hours: "5.0000", age_hours: "100.0000" }))).toBe("Reply late");
    });

    it("does not age a ticket with no status", () => {
      expect(lateLabel(ticket({ status: null, age_hours: "100.0000" }))).toBeNull();
    });

    it("still judges a recorded time on a ticket with no status", () => {
      expect(lateLabel(ticket({ status: null, resolution_hours: "30.0000", age_hours: "100.0000" }))).toBe("Resolution late");
    });
  });

  describe("with a target missing", () => {
    it("is null when neither stage has a target", () => {
      expect(lateLabel(ticket({ sla_response_hours: null, sla_resolution_hours: null, age_hours: "100.0000" }))).toBeNull();
    });

    it("does not judge a recorded time with no target", () => {
      expect(lateLabel(ticket({
        status: "resolved",
        first_response_hours: "100.0000",
        sla_response_hours: null,
        resolution_hours: "100.0000",
        sla_resolution_hours: null,
      }))).toBeNull();
    });

    it("judges the reply alone when the resolution has no target", () => {
      expect(lateLabel(ticket({ sla_resolution_hours: null, age_hours: "100.0000" }))).toBe("Reply late");
    });

    it("judges the resolution alone when the reply has no target", () => {
      expect(lateLabel(ticket({ sla_response_hours: null, age_hours: "100.0000" }))).toBe("Resolution late");
    });
  });
});
