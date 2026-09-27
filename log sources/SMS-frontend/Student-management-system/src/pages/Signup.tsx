import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Signup() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!username || !email || !password || !confirmPassword) {
      alert("Please fill all fields");
      return;
    }

    if (password !== confirmPassword) {
      alert("Passwords do not match");
      return;
    }

    // After successful signup → go to login
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 p-4">
      <div className="w-full max-w-md bg-background p-8 rounded-2xl shadow-lg">

        {/* Logo */}
        <div className="flex justify-center mb-6">
  <div className="w-16 h-16 bg-primary rounded-xl flex items-center justify-center">
    <img
      src="/kdu-logo.png"
      alt="KDU Logo"
      className="w-11 h-11 object-contain"
    />
  </div>
</div>

        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold">Administrator Sign Up</h1>
          <p className="text-sm text-muted-foreground mt-1">
            KDU Student Management System
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">

          <div>
            <Label>Username</Label>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div>
            <Label>Email Address</Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div>
            <Label>Confirm Password</Label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          <Button type="submit" className="w-full h-11">
            <UserPlus className="w-4 h-4 mr-2" />
            Create Account
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-muted-foreground">
            Already have an account?
          </span>{" "}
          <span
            onClick={() => navigate("/login")}
            className="text-primary font-medium cursor-pointer hover:underline"
          >
            Sign In
          </span>
        </div>
      </div>
    </div>
  );
}