import Link from 'next/link';
import { AuthShell } from '@/components/auth/auth-shell';
import { SignUpForm } from '@/components/auth/sign-up-form';

export const metadata = { title: 'Create account · StockPilot' };

export default function SignUpPage() {
  return (
    <AuthShell
      title="Create your account"
      subtitle="Start using StockPilot in under a minute"
      footer={
        <>
          Already have an account?{' '}
          <Link href="/signin" className="font-medium text-foreground hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <SignUpForm />
    </AuthShell>
  );
}
