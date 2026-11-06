/**
 * The research facade deliberately parses a small query grammar, not natural-language intent.
 * The same strict ListWindowsInput schema validates structured and lexical filters.
 */
import { z } from "zod";
import { ListWindowsInput } from "./schemas.js";

export class QuerySyntaxError extends Error {}

function tokens(query: string): { value: string; operator: boolean }[] {
  const result: { value: string; operator: boolean }[] = [];
  let token = "";
  let operator = false;
  let quoted = false;
  let started = false;
  for (let i = 0; i < query.length; i++) {
    const c = query[i]!;
    if (c === '"') {
      quoted = !quoted;
      started = true;
    } else if (c === "\\") {
      const next = query[++i];
      if (next !== "\\" && next !== '"')
        throw new QuerySyntaxError(
          "Only escaped quotes and backslashes are supported",
        );
      token += next;
      started = true;
    } else if (/\s/u.test(c) && !quoted) {
      if (started) result.push({ value: token, operator });
      token = "";
      operator = false;
      started = false;
    } else {
      if (c === ":" && !quoted && /^[A-Za-z_]+$/u.test(token)) operator = true;
      token += c;
      started = true;
    }
  }
  if (quoted) throw new QuerySyntaxError("Unclosed quoted phrase");
  if (started) result.push({ value: token, operator });
  return result;
}

const operators: Record<string, string> = {
  agency: "agency",
  docket: "docket_id",
  rin: "rin",
  status: "status",
  confidence: "confidence",
  type: "window_type",
  after: "closes_after",
  before: "closes_before",
  close: "close_mode",
  offset: "offset",
};

export function parseSearchQuery(
  query: string,
): z.infer<typeof ListWindowsInput> {
  const filters: Record<string, unknown> = { limit: 10 };
  const words: string[] = [];
  for (const token of tokens(query)) {
    const match = token.operator
      ? /^([A-Za-z_]+):(.*)$/u.exec(token.value)
      : null;
    if (!match) {
      words.push(token.value);
      continue;
    }
    const key = operators[match[1]!];
    if (!key)
      throw new QuerySyntaxError(`Unsupported query operator: ${match[1]}`);
    if (key in filters)
      throw new QuerySyntaxError(`Repeated query operator: ${match[1]}`);
    if (!match[2]) throw new QuerySyntaxError(`Missing value for ${match[1]}`);
    if (key === "offset") {
      if (!/^\d+$/u.test(match[2]))
        throw new QuerySyntaxError("offset must be a nonnegative integer");
      filters[key] = Number(match[2]);
    } else filters[key] = match[2];
  }
  if (words.length) filters.keyword = words.join(" ");
  return ListWindowsInput.parse(filters);
}

export function nextSearchQuery(
  filters: z.infer<typeof ListWindowsInput>,
  offset: number,
): string {
  const parts: string[] = [];
  if (filters.keyword) parts.push(JSON.stringify(filters.keyword));
  for (const [operator, key] of Object.entries(operators)) {
    if (key === "offset") continue;
    const value = (filters as Record<string, unknown>)[key];
    if (value !== undefined) parts.push(`${operator}:${JSON.stringify(value)}`);
  }
  parts.push(`offset:${offset}`);
  const result = parts.join(" ");
  if (result.length > 500)
    throw new QuerySyntaxError(
      "The next query exceeds 500 characters; narrow the search",
    );
  return result;
}
