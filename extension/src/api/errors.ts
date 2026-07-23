/** API errors from Cliperry backend. */

export class ApiError extends Error {
  readonly statusCode: number;
  readonly code?: string;
  readonly payload?: unknown;

  constructor(
    message: string,
    options: { statusCode: number; code?: string; payload?: unknown } = {
      statusCode: 0,
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.statusCode = options.statusCode;
    this.code = options.code;
    this.payload = options.payload;
  }
}

export function toUserMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Неизвестная ошибка сети";
}
