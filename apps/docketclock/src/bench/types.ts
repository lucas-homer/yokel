/**
 * Agent-vs-DocketClock benchmark — shared shapes (design: the "Agent vs DocketClock: test design" doc).
 *
 * An Item is one question with its answer key. An Answer is what an arm returned, in the fixed shape
 * every arm is asked for. A Grade is the deterministic score of one Answer against one Item.
 */

export type Stratum =
  | "pin" // a human pin_close verdict: the cases where FR and Regulations.gov disagreed
  | "withdrawn" // a human confirm_withdrawn verdict
  | "escalate" // a human escalate verdict (#127): no document resolves it
  | "miss" // a post-close accuracy record with was_correct = false
  | "routine" // a post-close accuracy record with was_correct = true
  | "point_in_time" // memory: what Regulations.gov showed on a past date
  | "moved"; // memory: has the portal close date ever changed

export type Expectation =
  | { kind: "date"; date: string } // YYYY-MM-DD, America/New_York calendar date
  | { kind: "withdrawn" }
  | { kind: "unresolved" }
  | { kind: "moved"; moved: true; earlier_date: string }
  | { kind: "moved"; moved: false };

export interface Item {
  id: string;
  stratum: Stratum;
  /** "lookup" questions can be rebuilt from live sources; "memory" ones need someone who was watching. */
  family: "lookup" | "memory";
  ocd_id: string;
  question: string;
  expect: Expectation;
  refs: {
    fr_document_number: string | null;
    regs_document_id: string | null;
    docket_id: string | null;
  };
  /** Arm D: what DocketClock itself says, with no model in the loop. null where it does not apply. */
  docketclock: {
    /** The machine's own derivation with human verdicts hidden (review show --blind). */
    machine: ArmDAnswer | null;
    /** What DocketClock published (pins and all). */
    published: ArmDAnswer | null;
  };
  /** The key needs a hand check before it is trusted (misses and routine: graded by DocketClock's own check). */
  needs_check: boolean;
  /** Free-text provenance of the key, for the hand check. */
  key_note: string;
}

export type Confidence = "high" | "medium" | "low";

export interface Answer {
  answer_kind: "date" | "withdrawn" | "unresolved" | "yes" | "no";
  date: string | null;
  confidence: Confidence;
  round: string | null;
  sources: string[];
}

export type ArmDAnswer = Answer;

export type Grade =
  | "correct"
  | "honest_miss" // abstained or low confidence where the key was resolvable
  | "correct_abstention" // abstained where the key is escalate
  | "silent_wrong" // a confident (high/medium) wrong answer
  | "unparseable" // no answer in the required shape
  | "void"; // the run broke the arm's rules (blocked host, forbidden tool)

export const ARMS = ["A", "B", "C"] as const;
export type AgentArm = (typeof ARMS)[number];

export const MODELS = {
  opus: "claude-opus-5-5",
  fable: "claude-fable-5-2",
} as const;
export type ModelKey = keyof typeof MODELS;
