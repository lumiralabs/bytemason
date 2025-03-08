'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { motion } from 'framer-motion'
import Image from 'next/image'
import Link from 'next/link'

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    // Scene setup
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      750,
      window.innerWidth / window.innerHeight,
      2,
      100
    )
    camera.position.set(3, 4, 5)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    containerRef.current.appendChild(renderer.domElement)

    // Updated Galaxy parameters
    const parameters = {
      count: 80000,
      size: 0.02, // Slightly larger particles
      radius: 6,   // Larger radius
      branches: 12, // Fewer branches for more separation
      spin: 0.8,   // More spin for more pronounced spiral
      randomness: 0.2,
      randomnessPower: 4.5,
      insideColor: 0x00ff88, // Soft green
      outsideColor: 0x0066ff, // Deep blue
    }

    // Generate galaxy
    const positions = new Float32Array(parameters.count * 3)
    const colors = new Float32Array(parameters.count * 3)
    const colorInside = new THREE.Color(parameters.insideColor)
    const colorOutside = new THREE.Color(parameters.outsideColor)

    for (let i = 0; i < parameters.count; i++) {
      const i3 = i * 3
      const radius = Math.random() * parameters.radius
      const branchAngle = ((i % parameters.branches) / parameters.branches) * Math.PI * 4
      const spin = radius * parameters.spin

      const randomX = Math.pow(Math.random(), parameters.randomnessPower) * (Math.random() < 0.5 ? 1 : -1)
      const randomY = Math.pow(Math.random(), parameters.randomnessPower) * (Math.random() < 0.5 ? 1 : -1)
      const randomZ = Math.pow(Math.random(), parameters.randomnessPower) * (Math.random() < 0.5 ? 1 : -1)

      positions[i3] = Math.cos(branchAngle + spin) * radius + randomX
      positions[i3 + 1] = randomY
      positions[i3 + 2] = Math.sin(branchAngle + spin) * radius + randomZ

      const mixedColor = colorInside.clone()
      mixedColor.lerp(colorOutside, radius / parameters.radius)

      colors[i3] = mixedColor.r
      colors[i3 + 1] = mixedColor.g
      colors[i3 + 2] = mixedColor.b
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

    const material = new THREE.PointsMaterial({
      size: parameters.size,
      sizeAttenuation: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexColors: true
    })

    const points = new THREE.Points(geometry, material)
    points.position.y = -1.5
    scene.add(points)

    // Animation
    const animate = () => {
      points.rotation.y += 0.0004 // Slightly slower rotation
      renderer.render(scene, camera)
      requestAnimationFrame(animate)
    }
    animate()

    // Handle resize
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      geometry.dispose()
      material.dispose()
      renderer.dispose()
    }
  }, [])

  return (
    <main className="relative w-full h-screen overflow-hidden bg-black">
      <div ref={containerRef} className="absolute inset-0" />
      
      

      {/* Centered Launch Blog Badge - Adjusted for mobile */}
      <div className="absolute top-20 sm:top-12 left-1/2 -translate-x-1/2 z-20">
        <Link href="/blog">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
            whileHover={{ scale: 1.05 }}
            className="flex items-center gap-2 px-4 py-2 rounded-full
                      bg-gradient-to-r from-cyan-500/10 to-green-500/10
                      border border-cyan-500/20 cursor-pointer
                      hover:border-cyan-500/40 hover:from-cyan-500/20 hover:to-green-500/20
                      transition-all duration-300 backdrop-blur-sm"
          >
            <motion.div
              animate={{
                scale: [1, 1.2, 1],
                opacity: [0.5, 1, 0.5]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut"
              }}
              className="w-2 h-2 rounded-full bg-green-400 shadow-lg shadow-green-400/50"
            />
            <span className="text-sm bg-gradient-to-r from-cyan-300/90 to-green-300/90 bg-clip-text text-transparent">
              Launch Blog
            </span>
          </motion.div>
        </Link>
      </div>

      <div className="relative z-10 h-full flex items-center justify-center -mt-24 md:-mt-32">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
          className="text-center space-y-6 px-4 md:px-0"
        >
          {/* Title with character animation */}
          <motion.h1 
            className="font-pixel text-6xl sm:text-7xl md:text-8xl lg:text-9xl text-white"
          >
            {["B", "y", "t", "e", "M", "a", "s", "o", "n"].map((letter, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.5,
                  delay: i * 0.1,
                  type: "spring",
                  stiffness: 120,
                  damping: 10
                }}
                className="inline-block hover:text-white/80 transition-colors duration-300"
              >
                {letter}
              </motion.span>
            ))}
          </motion.h1>

          {/* Subheading with slide-up fade */}
          <motion.p 
            className="font-pixel text-lg sm:text-xl md:text-2xl lg:text-3xl text-white/70"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ 
              delay: 0.8,
              duration: 0.8,
              type: "spring",
              stiffness: 100
            }}
          >
            Prompt to code from your CLI by a team of AI agents
          </motion.p>

          {/* Buttons with staggered appearance */}
          <motion.div 
            className="flex flex-col sm:flex-row justify-center gap-4 sm:gap-6 pt-8 md:pt-10"
            variants={{
              hidden: { opacity: 0 },
              show: {
                opacity: 1,
                transition: {
                  staggerChildren: 0.2,
                  delayChildren: 1.2
                }
              }
            }}
            initial="hidden"
            animate="show"
          >
            <motion.a
              // href="https://lumiralabs.github.io/bytemason/"
              href='/documentation'
              variants={{
                hidden: { opacity: 0, y: 20 },
                show: { opacity: 1, y: 0 }
              }}
              whileHover={{ 
                scale: 1.05,
                backgroundColor: "rgba(255, 255, 255, 0.15)"
              }}
              whileTap={{ scale: 0.95 }}
              className="px-6 sm:px-8 py-3 bg-white/10 rounded-lg font-pixel text-base sm:text-lg md:text-xl text-white backdrop-blur-sm border border-white/20 hover:border-white/40 transition-all flex items-center justify-center gap-2"
            >
              <span>Documentation</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 md:w-5 md:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 17l9.2-9.2M17 17V7H7"/>
              </svg>
            </motion.a>
            
            <motion.a
              href="https://github.com/lumiralabs/bytemason"
              target="_blank"
              rel="noopener noreferrer"
              variants={{
                hidden: { opacity: 0, y: 20 },
                show: { opacity: 1, y: 0 }
              }}
              whileHover={{ 
                scale: 1.05,
                backgroundColor: "rgba(255, 255, 255, 0.15)"
              }}
              whileTap={{ scale: 0.95 }}
              className="px-6 sm:px-8 py-3 bg-white/10 rounded-lg font-pixel text-base sm:text-lg md:text-xl text-white backdrop-blur-sm border border-white/20 hover:border-white/40 transition-all flex items-center justify-center gap-2"
            >
              <span>Open Source</span>
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 md:w-5 md:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
              </svg>
            </motion.a>
          </motion.div>
        </motion.div>
      </div>
    </main>
  )
}
