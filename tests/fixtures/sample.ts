export interface UserProfile {
    id: string;
    username: string;
}

export type AuthToken = string;

export function verifyToken(token: AuthToken): boolean {
    return token.length > 0;
}

export const API_ENDPOINT = "https://api.domain.com";

export const logoutUser = async () => {
    return true;
};

export class SessionManager {
    createSession() {}
}
