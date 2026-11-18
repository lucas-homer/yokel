/**
 * adjudicator/model.ts — THE live adjudicator model. Every LLM call goes through Cloudflare AI Gateway, so
 * this AI Gateway catalog id (https://developers.cloudflare.com/ai/models/) is the whole choice.
 *
 * Changing it re-adjudicates: verdicts are cached per `${model}@${rulebook_version}`, so a new model asks
 * each question afresh (bounded by the per-cycle escalation cap). Pick a candidate with the
 * "Eval — compare models" workflow first; the weekly eval-chain gate then runs against this same constant.
 */
export const ADJUDICATOR_MODEL = "google/gemini-3.1-flash-lite";
