"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { getCurrentUser, login } from "@/src/lib/api/auth";
import { ApiError } from "@/src/lib/api/client";
import { validateLoginInput } from "@/src/lib/auth/validation";

import styles from "./login.module.css";

export function LoginForm() {
  const router = useRouter();
  const [userName, setUserName] = useState("");
  const [password, setPassword] = useState("");
  const [isChecking, setIsChecking] = useState(true);
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((user) => {
        if (active) {
          router.replace(`/mypage/${user.user_id}/groups`);
        }
      })
      .catch((reason: unknown) => {
        if (active && !(reason instanceof ApiError && reason.status === 401)) {
          setError(reason instanceof Error ? reason.message : "認証状態を確認できませんでした");
        }
      })
      .finally(() => {
        if (active) {
          setIsChecking(false);
        }
      });

    return () => {
      active = false;
    };
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateLoginInput({ userName, password });
    if (validationError !== null) {
      setError(validationError);
      return;
    }

    setIsPending(true);
    setError(null);
    try {
      const result = await login({ user_name: userName, password });
      router.replace(`/mypage/${result.user.user_id}/groups`);
    } catch (reason: unknown) {
      setPassword("");
      setError(reason instanceof Error ? reason.message : "ログインに失敗しました");
      setIsPending(false);
    }
  }

  const disabled = isChecking || isPending;

  return (
    <form className={styles.form} onSubmit={handleSubmit} noValidate>
      <div className={styles.field}>
        <label htmlFor="user-name">ユーザー名</label>
        <input
          id="user-name"
          name="user_name"
          type="text"
          autoComplete="username"
          value={userName}
          onChange={(event) => setUserName(event.target.value)}
          maxLength={50}
          required
          disabled={disabled}
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="password">パスワード</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          maxLength={255}
          required
          disabled={disabled}
        />
      </div>

      {error !== null && (
        <p className={styles.error} role="alert" aria-live="polite">
          {error}
        </p>
      )}

      <button className={styles.submit} type="submit" disabled={disabled}>
        {isChecking ? "認証確認中..." : isPending ? "ログイン中..." : "ログイン"}
      </button>
    </form>
  );
}
