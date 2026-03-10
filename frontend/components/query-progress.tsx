"use client"

import { useState, useEffect } from "react"
import { Check, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

const STEPS = [
  { label: "Understanding your question", duration: 600 },
  { label: "Decomposing into sub-queries", duration: 800 },
  { label: "Generating SQL", duration: 1000 },
  { label: "Executing queries", duration: 1200 },
  { label: "Analyzing results", duration: 800 },
]

export function QueryProgress() {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    let totalDelay = 0
    const timers: NodeJS.Timeout[] = []

    STEPS.forEach((step, index) => {
      if (index > 0) {
        totalDelay += STEPS[index - 1].duration
        const timer = setTimeout(() => {
          setCurrentStep(index)
        }, totalDelay)
        timers.push(timer)
      }
    })

    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="w-full max-w-md">
      <div className="flex items-center justify-center mb-8">
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
            <span className="text-[10px] font-bold text-primary-foreground">
              {currentStep + 1}
            </span>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {STEPS.map((step, index) => {
          const isCompleted = index < currentStep
          const isActive = index === currentStep
          const isPending = index > currentStep

          return (
            <div
              key={index}
              className={cn(
                "flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300",
                isActive && "bg-primary/10 border border-primary/20",
                isCompleted && "opacity-60",
                isPending && "opacity-40"
              )}
            >
              <div
                className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300",
                  isCompleted && "bg-success text-success-foreground",
                  isActive && "bg-primary text-primary-foreground",
                  isPending && "bg-muted text-muted-foreground"
                )}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4" />
                ) : isActive ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <span className="text-xs font-medium">{index + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  "text-sm transition-colors duration-300",
                  isActive && "text-foreground font-medium",
                  isCompleted && "text-muted-foreground",
                  isPending && "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
