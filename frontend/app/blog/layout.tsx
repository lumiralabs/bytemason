import { spaceGrotesk } from '../fonts'

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${spaceGrotesk.className} antialiased selection:bg-cyan-500/20 selection:text-cyan-200`}>
      {children}
    </div>
  )
} 