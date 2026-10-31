import { zodResolver } from "@hookform/resolvers/zod";
import { IconBook2 } from "@tabler/icons-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router";
import { z } from "zod";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { Button, ErrorBanner, Field, Input } from "../components/ui";

const schema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type LoginValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const from =
    (location.state as { from?: string } | null)?.from &&
    (location.state as { from?: string }).from !== "/login"
      ? (location.state as { from?: string }).from!
      : "/";

  const onSubmit = handleSubmit(async (values) => {
    setError(null);
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not sign in. Try again.",
      );
    }
  });

  return (
    <main className="login-shell">
      <section className="login-brand" aria-hidden="true">
        <div className="brand-mark">
          <IconBook2 size={26} stroke={1.7} />
          <span>Scriptorium</span>
        </div>
        <div className="login-brand-copy">
          <p className="eyebrow">Self-hosted documentation</p>
          <h1>Write the book. Publish the library.</h1>
          <p>
            A calm, structured editor for teams that care about durable URLs,
            clean Sphinx output, and owning their own content.
          </p>
        </div>
        <p className="login-brand-foot">
          © {new Date().getFullYear()} Tech4TIME
        </p>
      </section>

      <section className="login-panel">
        <div className="login-card">
          <p className="eyebrow">Librarian sign in</p>
          <h2>Welcome back</h2>
          <p className="muted">
            Use the account created by your Scriptorium administrator.
          </p>
          <form onSubmit={onSubmit} noValidate>
            <ErrorBanner message={error} />
            <Field label="Email">
              <Input
                type="email"
                autoComplete="username"
                autoFocus
                {...register("email")}
              />
              {errors.email ? (
                <span className="field-error">{errors.email.message}</span>
              ) : null}
            </Field>
            <Field label="Password">
              <Input
                type="password"
                autoComplete="current-password"
                {...register("password")}
              />
              {errors.password ? (
                <span className="field-error">{errors.password.message}</span>
              ) : null}
            </Field>
            <Button
              type="submit"
              variant="primary"
              className="button-block"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          <p className="login-help">
            No open registration. Ask an administrator if you need access.
          </p>
        </div>
      </section>
    </main>
  );
}
