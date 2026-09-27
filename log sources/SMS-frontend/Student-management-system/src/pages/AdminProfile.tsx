import { useState, useEffect } from "react";
import { User, Mail, Shield, Loader2, ArrowLeft, Save, Edit3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useNavigate } from "react-router-dom";
import { apiGet, apiPut } from "@/lib/api";
import { toast } from "sonner";

interface AdminDetails {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
}

export default function AdminProfile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const [formData, setFormData] = useState<AdminDetails>({
    username: "",
    email: "",
    firstName: "",
    lastName: "",
  });

  const [errors, setErrors] = useState<Partial<AdminDetails>>({});

  // Get current username from JWT
  const getCurrentUsername = () => {
    const token = localStorage.getItem("jwt_token");
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.sub ?? payload.username ?? payload.name;
    } catch {
      return null;
    }
  };

  useEffect(() => {
    const fetchProfile = async () => {
      const username = getCurrentUsername();
      if (!username) {
        toast.error("Session error. Please login again.");
        navigate("/login");
        return;
      }

      setLoading(true);
      try {
        // Fetch current admin details
        const data = await apiGet<AdminDetails>(`/api/v1/auth/get-admin/${username}`);
        setFormData(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load profile";
        toast.error("Error loading profile", { description: msg });
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [navigate]);

  const validate = () => {
    const newErrors: Partial<AdminDetails> = {};
    if (!formData.firstName.trim()) newErrors.firstName = "First name is required";
    if (!formData.lastName.trim()) newErrors.lastName = "Last name is required";
    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Invalid email format";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSaving(true);
    try {
      const username = getCurrentUsername();
      await apiPut(`/api/v1/auth/update/${username}`, {
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        // Username usually kept immutable in simple setups, 
        // but included if API supports it.
        username: formData.username
      });

      toast.success("Profile updated successfully");
      setIsEditing(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Update failed";
      toast.error("Failed to update profile", { description: msg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground animate-pulse">Loading administrator profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Button
          variant="ghost"
          onClick={() => navigate("/dashboard")}
          className="mb-4 -ml-2 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
        <h1 className="page-title">Admin Profile</h1>
        <p className="page-description">
          Manage your personal details and account settings.
        </p>
      </div>

      <div className="grid gap-6 max-w-2xl">
        <Card className="border-t-4 border-t-primary shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-xl">Personal Information</CardTitle>
                  <CardDescription>Update your public profile details</CardDescription>
                </div>
              </div>
              {!isEditing && (
                <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                  <Edit3 className="h-4 w-4 mr-2" />
                  Edit Profile
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSave} className="space-y-6">
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="firstName">First Name</Label>
                  <Input
                    id="firstName"
                    value={formData.firstName}
                    onChange={(e) => setFormData({ ...formData, firstName: e.target.value })}
                    disabled={!isEditing || saving}
                    placeholder="Enter first name"
                    className={errors.firstName ? "border-destructive" : ""}
                  />
                  {errors.firstName && <p className="text-xs text-destructive">{errors.firstName}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="lastName">Last Name</Label>
                  <Input
                    id="lastName"
                    value={formData.lastName}
                    onChange={(e) => setFormData({ ...formData, lastName: e.target.value })}
                    disabled={!isEditing || saving}
                    placeholder="Enter last name"
                    className={errors.lastName ? "border-destructive" : ""}
                  />
                  {errors.lastName && <p className="text-xs text-destructive">{errors.lastName}</p>}
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="flex items-center gap-2">
                    <Mail className="h-3 w-3" />
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    disabled={!isEditing || saving}
                    placeholder="admin@kdu.ac.lk"
                    className={errors.email ? "border-destructive" : ""}
                  />
                  {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="username" className="flex items-center gap-2">
                    <Shield className="h-3 w-3" />
                    Username
                  </Label>
                  <Input
                    id="username"
                    value={formData.username}
                    disabled={true} // Usually username is the unique ID and immutable
                    className="bg-muted font-medium"
                  />
                  <p className="text-[10px] text-muted-foreground italic">
                    Username is used for system identification and cannot be changed.
                  </p>
                </div>
              </div>

              {isEditing && (
                <div className="flex gap-3 pt-4 border-t border-border">
                  <Button type="submit" disabled={saving}>
                    {saving ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="h-4 w-4 mr-2" />
                    )}
                    {saving ? "Saving Changes..." : "Save Changes"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setIsEditing(false);
                      setErrors({});
                    }}
                    disabled={saving}
                  >
                    Cancel
                  </Button>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Info Card */}
        {!isEditing && (
          <div className="bg-primary/5 border border-primary/20 rounded-lg p-4 flex gap-3">
            <Shield className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold text-primary">Security Note</p>
              <p className="text-muted-foreground">
                Your profile details are used for audit logging. Ensure your email is up to date to receive system notifications.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
