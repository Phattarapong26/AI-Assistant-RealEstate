/**
 * API client for the AI Property Consultant backend.
 *
 * The backend URL comes from VITE_API_BASE_URL so the same build can point at
 * a local server during development and at the real server in production.
 */

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000/api";

const TOKEN_KEY = "property_ai_token";
const CURRENT_USER_KEY = "property_ai_current_user";

// Types
export interface PropertyQuery {
  query: string;
  consultation_style?: string;
  session_id?: string;
  chat_room_id?: string;
  save_message?: boolean;
  timestamp?: number;
  get_history?: boolean;
  language?: string;
}

export interface ChatResponse {
  response: string;
  session_id?: string;
  chat_room_id?: string;
  properties?: Array<Record<string, string>>;
  messages?: ChatHistory["messages"];
}

export interface ChatHistory {
  chat_room_id: string;
  messages: Array<{
    role: "user" | "assistant";
    content: string;
    timestamp: number;
    properties?: Array<Record<string, string>>;
  }>;
}

export interface UploadResponse {
  message: string;
  file_id: string;
  num_records: number;
}

export interface ConsultationStyles {
  [key: string]: string;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
}

// --- Session token helpers ---------------------------------------------------
export const getAuthToken = (): string | null => localStorage.getItem(TOKEN_KEY);

export const setAuthSession = (token: string, user: AuthUser): void => {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
};

export const clearAuthSession = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(CURRENT_USER_KEY);
};

const authHeaders = (): Record<string, string> => {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/** Turn a failed response into a readable Thai error message. */
const readError = async (response: Response, fallback: string): Promise<string> => {
  try {
    const data = await response.json();
    if (typeof data?.detail === "string") return data.detail;
  } catch {
    /* the body was not JSON */
  }
  return fallback;
};

// --- Authentication ----------------------------------------------------------
export const registerUser = async (
  name: string,
  email: string,
  password: string
): Promise<AuthUser> => {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password }),
  });

  if (!response.ok) {
    throw new Error(await readError(response, "ลงทะเบียนไม่สำเร็จ กรุณาลองใหม่อีกครั้ง"));
  }

  const data = await response.json();
  setAuthSession(data.token, data.user);
  return data.user;
};

export const loginUser = async (email: string, password: string): Promise<AuthUser> => {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    throw new Error(await readError(response, "อีเมลหรือรหัสผ่านไม่ถูกต้อง"));
  }

  const data = await response.json();
  setAuthSession(data.token, data.user);
  return data.user;
};

// --- Chat --------------------------------------------------------------------
export const sendChatMessage = async (queryData: PropertyQuery): Promise<ChatResponse> => {
  const payload: PropertyQuery = { ...queryData };

  if (payload.chat_room_id && !payload.session_id) {
    payload.session_id = payload.chat_room_id;
  }
  payload.save_message = true;
  payload.timestamp = Date.now();

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(
      await readError(response, "ส่งข้อความไม่สำเร็จ กรุณาลองใหม่อีกครั้ง")
    );
  }

  const data: ChatResponse = await response.json();
  if (data.session_id && !data.chat_room_id) {
    data.chat_room_id = data.session_id;
  }
  return data;
};

/** Load a conversation that is stored on the server. */
export const getChatRoomHistory = async (chatRoomId: string): Promise<ChatHistory> => {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        session_id: chatRoomId,
        chat_room_id: chatRoomId,
        query: "",
        get_history: true,
        consultation_style: localStorage.getItem("consultationStyle") || "formal",
      }),
    });

    if (!response.ok) {
      return { chat_room_id: chatRoomId, messages: [] };
    }

    const data = await response.json();
    return { chat_room_id: chatRoomId, messages: data.messages ?? [] };
  } catch (error) {
    console.error("Error fetching chat history:", error);
    return { chat_room_id: chatRoomId, messages: [] };
  }
};

/**
 * The backend stores every message as part of /chat, so the UI does not need
 * to push history separately. Kept for API compatibility with the components.
 */
export const saveChatHistory = async (
  _chatRoomId?: string,
  _messages?: unknown
): Promise<boolean> => true;

// --- Property catalogue ------------------------------------------------------
export const uploadPropertyFile = async (
  file: File,
  consultationStyle: string = "formal"
): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("consultation_style", consultationStyle);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(
      await readError(response, "อัปโหลดไฟล์ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง")
    );
  }

  return response.json();
};

export const getConsultationStyles = async (): Promise<ConsultationStyles> => {
  try {
    const response = await fetch(`${API_BASE_URL}/styles`);
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Error fetching consultation styles:", error);
    return {
      formal: "ทางการ",
      casual: "ทั่วไป",
      friendly: "เป็นกันเอง",
      professional: "มืออาชีพ",
    };
  }
};
