import { LoginForm } from "./login-form";
import styles from "./login.module.css";

export default function LoginPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card} aria-labelledby="login-title">
        <h1 className={styles.title} id="login-title">
          ログイン
        </h1>
        <p className={styles.description}>アノテーション作業進捗管理</p>
        <LoginForm />
      </section>
    </main>
  );
}
