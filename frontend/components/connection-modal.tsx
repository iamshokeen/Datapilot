"use client"

import { useState } from "react"
import { Database, Eye, EyeOff, Loader2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import type { Connection } from "@/lib/types"
import { connectDatabase } from "@/lib/api"

interface ConnectionModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConnect: (connection: Connection) => void
}

export function ConnectionModal({
  open,
  onOpenChange,
  onConnect,
}: ConnectionModalProps) {
  const [isConnecting, setIsConnecting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    alias: "",
    host: "",
    port: "5433",
    database: "",
    username: "",
    password: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsConnecting(true)
    setError(null)

    try {
      const result = await connectDatabase({
        alias: formData.alias || formData.database,
        host: formData.host,
        port: parseInt(formData.port),
        database: formData.database,
        username: formData.username,
        password: formData.password,
      })

      onConnect({
        id: result.connection_id,
        alias: formData.alias || formData.database,
        host: formData.host,
        port: parseInt(formData.port),
        database: formData.database,
        username: formData.username,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed")
    } finally {
      setIsConnecting(false)
    }
  }

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [field]: e.target.value }))
  }

  const isValid =
    formData.host && formData.port && formData.database && formData.username && formData.password

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Database className="w-5 h-5 text-primary" />
            </div>
            <div>
              <DialogTitle className="text-foreground">Connect Database</DialogTitle>
              <DialogDescription className="text-muted-foreground">
                Enter your PostgreSQL connection details
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="mt-2">
          <FieldGroup>
            <Field>
              <FieldLabel className="text-sm text-foreground">Connection Alias</FieldLabel>
              <Input
                placeholder="My Production DB"
                value={formData.alias}
                onChange={handleChange("alias")}
                className="bg-input border-border text-foreground placeholder:text-muted-foreground"
              />
            </Field>

            <div className="grid grid-cols-3 gap-3">
              <Field className="col-span-2">
                <FieldLabel className="text-sm text-foreground">Host</FieldLabel>
                <Input
                  placeholder="localhost"
                  value={formData.host}
                  onChange={handleChange("host")}
                  required
                  className="bg-input border-border text-foreground placeholder:text-muted-foreground"
                />
              </Field>
              <Field>
                <FieldLabel className="text-sm text-foreground">Port</FieldLabel>
                <Input
                  placeholder="5432"
                  value={formData.port}
                  onChange={handleChange("port")}
                  required
                  className="bg-input border-border text-foreground placeholder:text-muted-foreground"
                />
              </Field>
            </div>

            <Field>
              <FieldLabel className="text-sm text-foreground">Database Name</FieldLabel>
              <Input
                placeholder="lohono_production"
                value={formData.database}
                onChange={handleChange("database")}
                required
                className="bg-input border-border text-foreground placeholder:text-muted-foreground"
              />
            </Field>

            <Field>
              <FieldLabel className="text-sm text-foreground">Username</FieldLabel>
              <Input
                placeholder="postgres"
                value={formData.username}
                onChange={handleChange("username")}
                required
                className="bg-input border-border text-foreground placeholder:text-muted-foreground"
              />
            </Field>

            <Field>
              <FieldLabel className="text-sm text-foreground">Password</FieldLabel>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter password"
                  value={formData.password}
                  onChange={handleChange("password")}
                  required
                  className="bg-input border-border text-foreground placeholder:text-muted-foreground pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </Field>
          </FieldGroup>

          {error && (
            <p className="text-sm text-red-400 mt-4">{error}</p>
          )}

          <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              onClick={() => onOpenChange(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isValid || isConnecting}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {isConnecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                "Connect"
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
