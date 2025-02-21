import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import configparser
from datetime import datetime
import json
import re
from tkinter import ttk, StringVar
import keyring
import base64


class DatabaseSelectDialog:
    def __init__(self, parent, connection_info):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Database")
        self.dialog.geometry("300x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.connection_info = connection_info
        self.selected_db = None
        
        # Create UI elements
        ttk.Label(self.dialog, text="Available Databases:").pack(pady=5)
        
        # Create listbox with scrollbar
        frame = ttk.Frame(self.dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.listbox = tk.Listbox(frame)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Select", command=self.on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT, padx=5)
        
        # Load databases
        self.load_databases()
        
        # Center dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
    def load_databases(self):
        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.connection_info["password"]
            
            result = subprocess.run([
                "psql",
                "-h", self.connection_info["host"],
                "-p", self.connection_info["port"],
                "-U", self.connection_info["username"],
                "-d", "postgres",
                "-t", "-A",
                "-c", "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
            ], env=env, check=True, capture_output=True, text=True)
            
            databases = [db.strip() for db in result.stdout.split('\n') if db.strip()]
            for db in databases:
                self.listbox.insert(tk.END, db)
                
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to fetch databases:\n{e.stderr}")
            self.dialog.destroy()
            
    def on_select(self):
        if self.listbox.curselection():
            self.selected_db = self.listbox.get(self.listbox.curselection())
            self.dialog.destroy()
            
    def on_cancel(self):
        self.dialog.destroy()


class PostgresGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PostgreSQL Import/Export Tool")
        self.root.minsize(600, 700)

        # Create style
        self.style = ttk.Style()
        self.style.configure('TButton', padding=5)
        self.style.configure('TLabelframe', padding=10)
        
        # Status bar
        self.status_var = StringVar()
        self.progress_var = StringVar()
        
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)

        # Load profiles
        self.profiles_file = "db_profiles.json"
        self.profiles = self.load_profiles()
        self.current_profile = None
        self.keyring_service = "pg_import_export"

        # Create frames
        self.create_profile_frame(main_container)
        self.create_connection_frame(main_container)
        self.create_action_frame(main_container)
        self.create_status_bar(main_container)

        # If profiles exist, load the first one
        if self.profiles:
            first_profile = next(iter(self.profiles))
            self.profile_var.set(first_profile)
            self.load_profile(first_profile)

        # Add tooltips
        self.create_tooltips()

    def load_profiles(self):
        if os.path.exists(self.profiles_file):
            with open(self.profiles_file, "r") as f:
                return json.load(f)
        return {}

    def save_profiles(self):
        with open(self.profiles_file, "w") as f:
            json.dump(self.profiles, f, indent=4)

    def create_profile_frame(self, parent):
        profile_frame = ttk.LabelFrame(
            parent, text="Connection Profiles", padding="10"
        )
        profile_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        # Profile selection
        ttk.Label(profile_frame, text="Profile:").grid(row=0, column=0, sticky="w")
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var)
        self.profile_combo["values"] = list(self.profiles.keys())
        self.profile_combo.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        self.profile_combo.bind(
            "<<ComboboxSelected>>", lambda e: self.load_profile(self.profile_var.get())
        )

        # Profile management buttons
        btn_frame = ttk.Frame(profile_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)

        ttk.Button(btn_frame, text="New Profile", command=self.new_profile).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Save Profile", command=self.save_profile).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(btn_frame, text="Delete Profile", command=self.delete_profile).pack(
            side=tk.LEFT, padx=2
        )

        profile_frame.columnconfigure(1, weight=1)

    def create_connection_frame(self, parent):
        connection_frame = ttk.LabelFrame(
            parent, text="Database Connection", padding="10"
        )
        connection_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Connection details
        labels = ["Host:", "Port:", "Username:", "Password:", "Database:"]
        self.connection_entries = {}

        for i, label in enumerate(labels):
            ttk.Label(connection_frame, text=label).grid(row=i, column=0, sticky="w")
            entry = ttk.Entry(connection_frame)
            if label == "Password:":
                entry.configure(show="*")
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            self.connection_entries[label.lower().rstrip(":")] = entry
            
            # Add database selection button
            if label == "Database:":
                ttk.Button(
                    connection_frame,
                    text="Select...",
                    command=self.select_database
                ).grid(row=i, column=2, padx=5, pady=2)

        # Add "Save Password" checkbox
        self.save_password_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            connection_frame,
            text="Save Password",
            variable=self.save_password_var
        ).grid(row=len(labels), column=0, columnspan=2, sticky="w")

        # Test connection button
        ttk.Button(
            connection_frame, text="Test Connection", command=self.test_connection
        ).grid(row=len(labels)+1, column=0, columnspan=3, pady=10)

        connection_frame.columnconfigure(1, weight=1)

    def create_action_frame(self, parent):
        action_frame = ttk.LabelFrame(parent, text="Actions", padding="10")
        action_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        # Export section
        ttk.Label(action_frame, text="Export Options:").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=5
        )

        self.export_type = tk.StringVar(value="full")
        ttk.Radiobutton(
            action_frame, text="Full Backup", variable=self.export_type, value="full"
        ).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(
            action_frame, text="Schema Only", variable=self.export_type, value="schema"
        ).grid(row=1, column=1, sticky="w")
        ttk.Radiobutton(
            action_frame, text="Data Only", variable=self.export_type, value="data"
        ).grid(row=1, column=2, sticky="w")

        ttk.Button(
            action_frame, text="Export Database", command=self.export_database
        ).grid(row=2, column=0, columnspan=3, pady=10)

        # Import section
        ttk.Label(action_frame, text="Import Options:").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=5
        )
        ttk.Button(
            action_frame, text="Import Database", command=self.import_database
        ).grid(row=4, column=0, columnspan=3, pady=10)

    def create_status_bar(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=100, column=0, sticky="ew", pady=(10,0))
        
        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0,10))
        
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=1, sticky="w")
        
        status_frame.columnconfigure(0, weight=1)
        self.status_var.set("Ready")

    def create_tooltips(self):
        self.add_tooltip(self.connection_entries['host'], "Database server hostname or IP address")
        self.add_tooltip(self.connection_entries['port'], "PostgreSQL server port (default: 5432)")
        self.add_tooltip(self.connection_entries['username'], "Database user name")
        self.add_tooltip(self.connection_entries['database'], "Name of the database to connect to")

    def add_tooltip(self, widget, text):
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
            
        widget.bind('<Enter>', show_tooltip)

    def new_profile(self):
        name = tk.simpledialog.askstring("New Profile", "Enter profile name:")
        if name:
            if name in self.profiles:
                messagebox.showerror("Error", "Profile name already exists!")
                return

            self.profiles[name] = {
                "host": "localhost",
                "port": "5432",
                "username": "postgres",
                "database": "",
            }
            self.profile_combo["values"] = list(self.profiles.keys())
            self.profile_var.set(name)
            self.load_profile(name)
            self.save_profiles()

    def save_profile(self):
        name = self.profile_var.get()
        if not name:
            messagebox.showerror("Error", "Please select or create a profile first!")
            return

        profile_data = {
            "host": self.connection_entries["host"].get(),
            "port": self.connection_entries["port"].get(),
            "username": self.connection_entries["username"].get(),
            "database": self.connection_entries["database"].get(),
            "has_saved_password": False
        }

        # Save password if checkbox is checked
        if self.save_password_var.get():
            password = self.connection_entries["password"].get()
            if password:
                # Create a unique key for this profile's password
                password_key = f"{name}_{profile_data['username']}"
                keyring.set_password(self.keyring_service, password_key, password)
                profile_data["has_saved_password"] = True

        self.profiles[name] = profile_data
        self.save_profiles()
        messagebox.showinfo("Success", f"Profile '{name}' saved successfully!")

    def load_profile(self, name):
        if name not in self.profiles:
            return

        profile = self.profiles[name]
        self.connection_entries["host"].delete(0, tk.END)
        self.connection_entries["host"].insert(0, profile["host"])

        self.connection_entries["port"].delete(0, tk.END)
        self.connection_entries["port"].insert(0, profile["port"])

        self.connection_entries["username"].delete(0, tk.END)
        self.connection_entries["username"].insert(0, profile["username"])

        self.connection_entries["database"].delete(0, tk.END)
        self.connection_entries["database"].insert(0, profile["database"])

        # Clear password entry
        self.connection_entries["password"].delete(0, tk.END)

        # Load saved password if it exists
        if profile.get("has_saved_password", False):
            password_key = f"{name}_{profile['username']}"
            saved_password = keyring.get_password(self.keyring_service, password_key)
            if saved_password:
                self.connection_entries["password"].insert(0, saved_password)
                self.save_password_var.set(True)
            else:
                self.save_password_var.set(False)
        else:
            self.save_password_var.set(False)

    def delete_profile(self):
        name = self.profile_var.get()
        if not name:
            messagebox.showerror("Error", "Please select a profile to delete!")
            return

        if messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete profile '{name}'?"
        ):
            # Delete saved password if it exists
            profile = self.profiles[name]
            if profile.get("has_saved_password", False):
                password_key = f"{name}_{profile['username']}"
                try:
                    keyring.delete_password(self.keyring_service, password_key)
                except:
                    pass  # Ignore errors when deleting password

            # Delete profile and update UI
            del self.profiles[name]
            self.save_profiles()
            self.profile_combo["values"] = list(self.profiles.keys())
            if self.profiles:
                first_profile = next(iter(self.profiles))
                self.profile_var.set(first_profile)
                self.load_profile(first_profile)
            else:
                self.profile_var.set("")
                for entry in self.connection_entries.values():
                    entry.delete(0, tk.END)
                self.save_password_var.set(False)

    def validate_port(self, value):
        if not value:
            return True
        return value.isdigit() and 1 <= int(value) <= 65535

    def validate_connection(self):
        try:
            # Validate host
            host = self.connection_entries["host"].get().strip()
            if not host:
                raise ValueError("Host cannot be empty")

            # Validate port
            port = self.connection_entries["port"].get().strip()
            if not port or not self.validate_port(port):
                raise ValueError("Port must be a number between 1 and 65535")

            # Validate username
            username = self.connection_entries["username"].get().strip()
            if not username:
                raise ValueError("Username cannot be empty")

            # Validate password
            password = self.connection_entries["password"].get()
            if not password:
                raise ValueError("Password cannot be empty")

            # Validate database name
            database = self.connection_entries["database"].get().strip()
            if not database:
                raise ValueError("Database name cannot be empty")
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', database):
                raise ValueError("Invalid database name format")

            return True
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return False

    def test_connection(self):
        if not self.validate_connection():
            return

        self.status_var.set("Testing connection...")
        self.progress_bar.start()
        self.root.update()

        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.connection_entries["password"].get()

            result = subprocess.run(
                [
                    "psql",
                    "-h", self.connection_entries["host"].get(),
                    "-p", self.connection_entries["port"].get(),
                    "-U", self.connection_entries["username"].get(),
                    "-d", self.connection_entries["database"].get(),
                    "-c", "SELECT version();",
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True
            )

            self.status_var.set("Connection successful")
            messagebox.showinfo("Success", "Connection successful!\n" + result.stdout.split('\n')[0])
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip()
            self.status_var.set("Connection failed")
            if "password authentication failed" in error_msg.lower():
                messagebox.showerror("Authentication Error", "Invalid username or password")
            elif "could not connect to server" in error_msg.lower():
                messagebox.showerror("Connection Error", "Could not connect to the database server.\nPlease check the host and port.")
            else:
                messagebox.showerror("Error", f"Connection failed:\n{error_msg}")
        except Exception as e:
            self.status_var.set("Connection failed")
            messagebox.showerror("Error", f"Unexpected error:\n{str(e)}")
        finally:
            self.progress_bar.stop()

    def export_database(self):
        if not self.validate_connection():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_name = self.profile_var.get()
        default_filename = f"{profile_name}_{self.connection_entries['database'].get()}_{timestamp}.sql"

        filename = filedialog.asksaveasfilename(
            defaultextension=".sql",
            initialfile=default_filename,
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")]
        )

        if not filename:
            return

        self.status_var.set("Exporting database...")
        self.progress_bar.start()
        self.root.update()

        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.connection_entries["password"].get()

            cmd = [
                "pg_dump",
                "-h", self.connection_entries["host"].get(),
                "-p", self.connection_entries["port"].get(),
                "-U", self.connection_entries["username"].get(),
                "-d", self.connection_entries["database"].get(),
            ]

            if self.export_type.get() == "schema":
                cmd.append("--schema-only")
            elif self.export_type.get() == "data":
                cmd.append("--data-only")

            with open(filename, "w") as f:
                subprocess.run(cmd, env=env, check=True, stdout=f)

            self.status_var.set("Export completed successfully")
            messagebox.showinfo("Success", f"Database exported successfully to:\n{filename}")
        except subprocess.CalledProcessError as e:
            self.status_var.set("Export failed")
            messagebox.showerror("Export Error", f"Export failed:\n{e.stderr.decode()}")
        except Exception as e:
            self.status_var.set("Export failed")
            messagebox.showerror("Error", f"Unexpected error during export:\n{str(e)}")
        finally:
            self.progress_bar.stop()

    def import_database(self):
        if not self.validate_connection():
            return

        filename = filedialog.askopenfilename(
            filetypes=[("SQL files", "*.sql"), ("All files", "*.*")]
        )

        if not filename:
            return

        if not messagebox.askyesno(
            "Confirm Import",
            "Importing may overwrite existing data. Are you sure you want to continue?",
        ):
            return

        self.status_var.set("Importing database...")
        self.progress_bar.start()
        self.root.update()

        try:
            env = os.environ.copy()
            env["PGPASSWORD"] = self.connection_entries["password"].get()

            with open(filename, "r") as f:
                subprocess.run(
                    [
                        "psql",
                        "-h", self.connection_entries["host"].get(),
                        "-p", self.connection_entries["port"].get(),
                        "-U", self.connection_entries["username"].get(),
                        "-d", self.connection_entries["database"].get(),
                    ],
                    env=env,
                    check=True,
                    stdin=f,
                )

            self.status_var.set("Import completed successfully")
            messagebox.showinfo("Success", "Database imported successfully!")
        except subprocess.CalledProcessError as e:
            self.status_var.set("Import failed")
            messagebox.showerror("Import Error", f"Import failed:\n{e.stderr.decode()}")
        except Exception as e:
            self.status_var.set("Import failed")
            messagebox.showerror("Error", f"Unexpected error during import:\n{str(e)}")
        finally:
            self.progress_bar.stop()

    def validate_connection(self):
        required_fields = ["host", "port", "username", "password", "database"]
        for field in required_fields:
            if not self.connection_entries[field].get():
                messagebox.showerror("Error", f"{field.capitalize()} is required!")
                return False
        return True

    def select_database(self):
        # First validate connection details
        host = self.connection_entries["host"].get().strip()
        port = self.connection_entries["port"].get().strip()
        username = self.connection_entries["username"].get().strip()
        password = self.connection_entries["password"].get()
        
        if not all([host, port, username, password]):
            messagebox.showerror(
                "Error",
                "Please fill in the host, port, username, and password fields first."
            )
            return
            
        # Show database selection dialog
        connection_info = {
            "host": host,
            "port": port,
            "username": username,
            "password": password
        }
        
        dialog = DatabaseSelectDialog(self.root, connection_info)
        self.root.wait_window(dialog.dialog)
        
        if dialog.selected_db:
            self.connection_entries["database"].delete(0, tk.END)
            self.connection_entries["database"].insert(0, dialog.selected_db)


if __name__ == "__main__":
    root = tk.Tk()
    app = PostgresGUI(root)
    root.mainloop()

