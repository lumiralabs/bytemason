import { Footer, LastUpdated, Layout, Navbar } from 'nextra-theme-docs'
import { getPageMap } from 'nextra/page-map'
import 'nextra-theme-docs/style.css'
import { GitHubIcon } from 'nextra/icons'
import { spaceGrotesk } from '../fonts'

const navbar = (
  <Navbar
      logo={
        <>
          <img src="/favicon.ico" alt="ByteMason" className="w-8 h-8" />
          <span style={{ marginLeft: '.4em', fontWeight: 800 }}>
            ByteMason
          </span>
        </>
      }
    projectLink='https://github.com/lumiralabs/bytemason'
    projectIcon={<GitHubIcon height="24" />}
  />
)
const footer = <Footer>{new Date().getFullYear()} © Lumira Labs.</Footer>
 
export default async function DocLayout({ children }: { children: React.ReactNode; }) {
  return (
    <div className={spaceGrotesk.className}>
      <Layout
        navbar={navbar}
        pageMap={await getPageMap()}
        docsRepositoryBase="https://github.com/lumiralabs/bytemason"
        footer={footer}
        lastUpdated={<LastUpdated />}
        darkMode={false}
      >
        {children}
      </Layout>
    </div>
  )
}