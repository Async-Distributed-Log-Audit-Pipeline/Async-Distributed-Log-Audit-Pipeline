 import { AdminSidebar } from "./AdminSidebar";
 import { Outlet } from "react-router-dom";
 
 export function AdminLayout() {
   return (
     <div className="min-h-screen flex w-full">
       <AdminSidebar />
       <main className="flex-1 lg:pl-64">
         <Outlet />
       </main>
     </div>
   );
 }