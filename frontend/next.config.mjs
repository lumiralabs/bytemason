import nextra from 'nextra'
 

/** @type {import('next').NextConfig} */
const nextConfig = {};

const withNextra = nextra({
  contentDirBasePath: '/documentation',
  defaultShowCopyCode: true,
})
   
export default withNextra(nextConfig)
