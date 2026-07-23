/**
 * Messaging helpers for content / background / popup.
 */

import {
  isCliperryEvent,
  type CliperryEvent,
  type CliperryEventType,
} from "./events";

type EventOf<T extends CliperryEventType> = Extract<CliperryEvent, { type: T }>;

export async function sendEvent<T extends CliperryEvent>(
  event: T,
): Promise<CliperryEvent | void> {
  try {
    const response = await chrome.runtime.sendMessage(event);
    if (isCliperryEvent(response)) {
      return response;
    }
  } catch (error) {
    // Popup closed / no receiver is normal for fire-and-forget broadcasts.
    if (isNoReceiverError(error)) {
      return;
    }
    throw error;
  }
}

export async function sendToTab<T extends CliperryEvent>(
  tabId: number,
  event: T,
): Promise<CliperryEvent | void> {
  try {
    const response = await chrome.tabs.sendMessage(tabId, event);
    if (isCliperryEvent(response)) {
      return response;
    }
  } catch (error) {
    if (isNoReceiverError(error)) {
      return;
    }
    throw error;
  }
}

export function onEvent(
  handler: (
    event: CliperryEvent,
    sender: chrome.runtime.MessageSender,
  ) => CliperryEvent | Promise<CliperryEvent | void> | void,
): () => void {
  const listener: Parameters<typeof chrome.runtime.onMessage.addListener>[0] = (
    message,
    sender,
    sendResponse,
  ) => {
    if (!isCliperryEvent(message)) {
      return false;
    }

    const result = handler(message, sender);
    if (result instanceof Promise) {
      void result
        .then((response) => {
          if (response) {
            sendResponse(response);
          }
        })
        .catch((error: unknown) => {
          const messageText =
            error instanceof Error ? error.message : "Unknown messaging error";
          sendResponse({ type: "ERROR", message: messageText } satisfies CliperryEvent);
        });
      return true;
    }

    if (result) {
      sendResponse(result);
    }
    return false;
  };

  chrome.runtime.onMessage.addListener(listener);
  return () => {
    chrome.runtime.onMessage.removeListener(listener);
  };
}

export async function requestEvent<
  TReq extends CliperryEvent,
  TRes extends CliperryEventType,
>(
  event: TReq,
  expect: TRes,
): Promise<EventOf<TRes> | null> {
  const response = await sendEvent(event);
  if (response && response.type === expect) {
    return response as EventOf<TRes>;
  }
  return null;
}

function isNoReceiverError(error: unknown): boolean {
  const text = error instanceof Error ? error.message : String(error);
  return (
    text.includes("Receiving end does not exist") ||
    text.includes("Could not establish connection")
  );
}
