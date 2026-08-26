import Link from "next/link";
import type { ReactNode } from "react";

export function HistoricShell({ step, children }: { step: 1 | 2 | 3; children: ReactNode }) {
  return <main className="historic-workspace"><header className="historic-topbar"><Link href="/" className="historic-brand">RiskChain <small>CAT intelligence</small></Link><nav aria-label="Event archive mode"><Link href="/?view=live">Live</Link><Link className="active" href="/historic">Historic</Link></nav></header><div className="historic-stepper" aria-label="Historic event workflow"><span className={step >= 1 ? "active" : ""}><b>1</b> Select event</span><i /><span className={step >= 2 ? "active" : ""}><b>2</b> Select data</span><i /><span className={step >= 3 ? "active" : ""}><b>3</b> Explore</span></div>{children}</main>;
}
