export type LoginInput = {
  userName: string;
  password: string;
};

export function validateLoginInput({
  userName,
  password,
}: LoginInput): string | null {
  if (userName.length === 0 || password.length === 0) {
    return "ユーザー名とパスワードを入力してください";
  }
  if (userName.length > 50 || password.length > 255) {
    return "入力できる文字数を超えています";
  }
  return null;
}
