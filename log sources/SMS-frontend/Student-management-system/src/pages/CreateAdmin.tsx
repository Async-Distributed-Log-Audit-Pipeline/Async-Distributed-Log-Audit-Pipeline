import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UserPlus, Loader2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { apiPost } from "@/lib/api";

export default function CreateAdmin() {
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        username: "",
        email: "",
        password: "",
        confirmPassword: "",
        firstName: "",
        lastName: "",
    });

    const [errors, setErrors] = useState({
        username: "",
        email: "",
        password: "",
        confirmPassword: "",
        firstName: "",
        lastName: "",
    });

    const [loading, setLoading] = useState(false);

    const validate = () => {
        const newErrors = {
            username: "",
            email: "",
            password: "",
            confirmPassword: "",
            firstName: "",
            lastName: "",
        };

        if (!formData.username.trim() || formData.username.length < 3 || formData.username.length > 50)
            newErrors.username = "Username must be between 3 and 50 characters";
        if (!formData.firstName.trim())
            newErrors.firstName = "First name is required";
        if (!formData.lastName.trim())
            newErrors.lastName = "Last name is required";
        if (!formData.email.trim())
            newErrors.email = "Email is required";
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email))
            newErrors.email = "Email must be valid";
        if (!formData.password || formData.password.length < 6)
            newErrors.password = "Password must be at least 6 characters";
        if (formData.password !== formData.confirmPassword)
            newErrors.confirmPassword = "Passwords do not match";

        setErrors(newErrors);
        return Object.values(newErrors).every((e) => !e);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!validate()) return;

        setLoading(true);
        try {
            // POST YOUR_API_BASE_URL/api/v1/auth/register  (adjust path to match your backend)
            await apiPost("/api/v1/auth/register", {
                username: formData.username,
                email: formData.email,
                password: formData.password,
                firstName: formData.firstName,
                lastName: formData.lastName,
            });
            toast.success("Admin account created successfully", {
                description: `Account for "${formData.username}" is ready.`,
            });
            navigate("/dashboard");
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to create admin";
            toast.error("Failed to create admin", { description: msg });
        } finally {
            setLoading(false);
        }
    };

    const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
        setFormData((prev) => ({ ...prev, [field]: e.target.value }));

    return (
        <div className="page-container">
            <Button variant="ghost" onClick={() => navigate("/dashboard")} className="mb-4">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
            </Button>

            <div className="page-header">
                <h1 className="page-title">Create Admin Account</h1>
                <p className="page-description">
                    Register a new administrator. Only existing admins can perform this action.
                </p>
            </div>

            <Card className="max-w-lg">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <UserPlus className="h-5 w-5" />
                        New Admin Details
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit} className="form-section">

                        {/* Name row */}
                        <div className="form-row">
                            <div className="input-wrapper">
                                <Label htmlFor="firstName">First Name</Label>
                                <Input
                                    id="firstName"
                                    placeholder="e.g. John"
                                    value={formData.firstName}
                                    onChange={set("firstName")}
                                    disabled={loading}
                                />
                                {errors.firstName && <p className="validation-message">{errors.firstName}</p>}
                            </div>
                            <div className="input-wrapper">
                                <Label htmlFor="lastName">Last Name</Label>
                                <Input
                                    id="lastName"
                                    placeholder="e.g. Perera"
                                    value={formData.lastName}
                                    onChange={set("lastName")}
                                    disabled={loading}
                                />
                                {errors.lastName && <p className="validation-message">{errors.lastName}</p>}
                            </div>
                        </div>

                        <div className="input-wrapper">
                            <Label htmlFor="username">Username</Label>
                            <Input
                                id="username"
                                placeholder="3–50 characters"
                                value={formData.username}
                                onChange={set("username")}
                                disabled={loading}
                            />
                            {errors.username && <p className="validation-message">{errors.username}</p>}
                        </div>

                        <div className="input-wrapper">
                            <Label htmlFor="email">Email Address</Label>
                            <Input
                                id="email"
                                type="email"
                                placeholder="admin@example.com"
                                value={formData.email}
                                onChange={set("email")}
                                disabled={loading}
                            />
                            {errors.email && <p className="validation-message">{errors.email}</p>}
                        </div>

                        <div className="input-wrapper">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                placeholder="Minimum 6 characters"
                                value={formData.password}
                                onChange={set("password")}
                                disabled={loading}
                            />
                            {errors.password && <p className="validation-message">{errors.password}</p>}
                        </div>

                        <div className="input-wrapper">
                            <Label htmlFor="confirmPassword">Confirm Password</Label>
                            <Input
                                id="confirmPassword"
                                type="password"
                                placeholder="Re-enter password"
                                value={formData.confirmPassword}
                                onChange={set("confirmPassword")}
                                disabled={loading}
                            />
                            {errors.confirmPassword && (
                                <p className="validation-message">{errors.confirmPassword}</p>
                            )}
                        </div>

                        <div className="flex gap-3 pt-4">
                            <Button type="submit" disabled={loading}>
                                {loading ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <UserPlus className="h-4 w-4 mr-2" />
                                )}
                                {loading ? "Creating…" : "Create Admin"}
                            </Button>
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => navigate("/dashboard")}
                                disabled={loading}
                            >
                                Cancel
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
}
