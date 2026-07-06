import { BookOpen } from 'lucide-react';
import { PlaceholderPage } from '@/components/placeholder-page';

export const metadata = { title: 'Journal · StockPilot' };

export default function JournalPage() {
  return (
    <PlaceholderPage
      title="Journal"
      breadcrumb="Journal"
      icon={BookOpen}
      plannedIn="Month 4"
      description="Per-trade journal in the tradition of Douglas / Elder. Every trade documented with reason, rule adherence, and lessons."
      features={[
        'Chronological log of every trade with filter/search',
        'Per-trade entry reason, exit reason, rule-adherence score',
        'Lessons-learned field for each closed trade',
        'Rule-violation flagging: which rule(s) I broke on losing trades',
        'Weekly reflection prompts (Douglas-style)',
        'Monthly synthesis: patterns of my mistakes',
      ]}
    />
  );
}
