/**
 * Question templates. Frozen per run: the runner records a hash of this file and of the system prompt,
 * and a change means a new run id. Phrased the way a practitioner asks, naming the document the way
 * a lawyer would find it (FR document number first, else the Regulations.gov document id).
 */
import type { Item } from "./types.js";

export function docLabel(refs: Item["refs"]): string {
  const parts: string[] = [];
  if (refs.fr_document_number)
    parts.push(`Federal Register document ${refs.fr_document_number}`);
  if (refs.regs_document_id)
    parts.push(
      refs.fr_document_number
        ? `(Regulations.gov document ${refs.regs_document_id})`
        : `Regulations.gov document ${refs.regs_document_id}`,
    );
  if (refs.docket_id) parts.push(`in docket ${refs.docket_id}`);
  return parts.join(" ");
}

export function deadlineQuestion(refs: Item["refs"]): string {
  return (
    `What is the last day to submit written comments on ${docLabel(refs)}? ` +
    `Give the operative deadline for the initial comment round as a calendar date in Eastern time, ` +
    `and cite the documents that establish it. If the comment period was withdrawn, say so. ` +
    `If the sources conflict and no document resolves the conflict, answer "unresolved".`
  );
}

export function pointInTimeQuestion(refs: Item["refs"], asOf: string): string {
  return (
    `On ${asOf}, what comment end date did Regulations.gov display for ${docLabel(refs)}? ` +
    `Answer with the date as it was shown on that day (Eastern time), not today's value.`
  );
}

export function movedQuestion(refs: Item["refs"]): string {
  return (
    `Has the comment end date that Regulations.gov shows for ${docLabel(refs)} ever changed since the ` +
    `document was first posted? Answer "yes" or "no". If yes, give the EARLIEST end date it showed.`
  );
}
