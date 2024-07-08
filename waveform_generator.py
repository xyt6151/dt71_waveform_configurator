import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from tkinter.scrolledtext import ScrolledText
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
import pyperclip
from scipy.interpolate import make_interp_spline

class WaveformGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Waveform Generator")

        # Menu Bar
        self.menu_bar = tk.Menu(root)
        root.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="Clear", command=self.clear_points)
        self.file_menu.add_command(label="Exit", command=root.quit)

        self.preset_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Preset", menu=self.preset_menu)
        self.preset_menu.add_command(label="Sine Wave", command=lambda: self.generate_preset('sine'))
        self.preset_menu.add_command(label="Sawtooth Wave", command=lambda: self.generate_preset('sawtooth'))
        self.preset_menu.add_command(label="Triangle Wave", command=lambda: self.generate_preset('triangle'))
        self.preset_menu.add_command(label="Square Wave", command=lambda: self.generate_preset('square'))

        self.view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)

        self.grid_x_menu = tk.Menu(self.view_menu, tearoff=0)
        self.grid_y_menu = tk.Menu(self.view_menu, tearoff=0)

        self.view_menu.add_cascade(label="Grid X", menu=self.grid_x_menu)
        self.view_menu.add_cascade(label="Grid Y", menu=self.grid_y_menu)
        self.view_menu.add_command(label="Resolution", command=self.change_resolution)

        self.grid_x_enabled = tk.BooleanVar(value=True)
        self.grid_y_enabled = tk.BooleanVar(value=True)

        self.grid_x_menu.add_checkbutton(label="Enabled", onvalue=True, offvalue=False, variable=self.grid_x_enabled, command=self.update_grid)
        self.grid_y_menu.add_checkbutton(label="Enabled", onvalue=True, offvalue=False, variable=self.grid_y_enabled, command=self.update_grid)

        for interval in [2, 5, 10, 25, 50]:
            self.grid_x_menu.add_radiobutton(label=f"{interval}%", command=lambda i=interval: self.set_grid_x_interval(i))

        for interval in [0.1 * i for i in range(1, 11)]:
            self.grid_y_menu.add_radiobutton(label=f"{interval} V", command=lambda i=interval: self.set_grid_y_interval(i))

        self.grid_x_interval = 10  # Default grid x interval
        self.grid_y_interval = 0.5  # Default grid y interval

        self.figure, self.ax = plt.subplots()
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 3)
        self.ax.set_xlabel('Position (%)')
        self.ax.set_ylabel('Voltage (V)')
        self.ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='lightgrey')

        self.line, = self.ax.plot([], [], 'r-')
        self.points, = self.ax.plot([], [], 'bo')
        self.selected_point = None

        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.canvas.mpl_connect('button_press_event', self.on_click)

        self.point_list = [(0, 1.5), (100, 1.5)]

        self.copy_button = tk.Button(root, text="Copy", command=self.copy_to_clipboard)
        self.copy_button.pack(side=tk.TOP, fill=tk.X)

        self.load_button = tk.Button(root, text="Load", command=self.load_waveform)
        self.load_button.pack(side=tk.TOP, fill=tk.X)

        self.table = ttk.Treeview(root, columns=("Position", "Voltage"), show='headings')
        self.table.heading("Position", text="Position (%)")
        self.table.heading("Voltage", text="Voltage (V)")
        self.table.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.smooth_button = tk.Button(root, text="Smooth", command=self.smooth_peak, state=tk.DISABLED)
        self.smooth_button.pack(side=tk.TOP, fill=tk.X)

        self.deselect_button = tk.Button(root, text="Deselect", command=self.deselect_point, state=tk.DISABLED)
        self.deselect_button.pack(side=tk.LEFT, fill=tk.X)

        self.delete_button = tk.Button(root, text="Delete", command=self.delete_point, state=tk.DISABLED)
        self.delete_button.pack(side=tk.RIGHT, fill=tk.X)

        self.status_bar = tk.Label(root, text="Point count: 2", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="About", menu=self.about_menu)
        self.about_menu.add_command(label="About this tool", command=self.show_about)

        self.table.bind("<ButtonRelease-1>", self.on_table_select)
        self.table.bind("<Double-1>", self.on_double_click)
        self.update_plot()
        self.update_table()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        x, y = event.xdata, event.ydata
        x = self.snap_to_grid(x, self.grid_x_interval)
        y = self.snap_to_grid(y, self.grid_y_interval)
        if event.button == 1:
            self.add_or_update_point(x, y)
        elif event.button == 3:
            self.delete_point_by_position(x, y)
        self.update_plot()
        self.update_table()

    def snap_to_grid(self, value, interval):
        return round(value / interval) * interval

    def add_or_update_point(self, x, y):
        if x < 1:  # If close to 0%, update 0% point
            x = 0
        elif x > 99:  # If close to 100%, update 100% point
            x = 100

        for i, (px, py) in enumerate(self.point_list):
            if px == x:
                self.point_list[i] = (x, y)
                if x == 0:
                    self.point_list[self.point_list.index((100, self.point_list[-1][1]))] = (100, y)
                elif x == 100:
                    self.point_list[self.point_list.index((0, self.point_list[0][1]))] = (0, y)
                break
        else:
            self.point_list.append((x, y))

        self.point_list.sort()
        self.update_status_bar()

    def delete_point_by_position(self, x, y):
        tolerance = 2
        self.point_list = [(px, py) for (px, py) in self.point_list if abs(px - x) > tolerance or abs(py - y) > tolerance]

        # Ensure points at 0% and 100% are present
        if (0, 1.5) not in self.point_list:
            self.point_list.append((0, 1.5))
        if (100, 1.5) not in self.point_list:
            self.point_list.append((100, 1.5))

        self.point_list.sort()
        self.update_status_bar()

    def delete_point(self):
        selected_item = self.table.selection()[0]
        position = float(self.table.item(selected_item, "values")[0])
        if position in [0, 100]:
            return  # Prevent deletion of 0% and 100% points

        self.point_list = [(x, y) for (x, y) in self.point_list if x != position]

        self.update_plot()
        self.update_table()
        self.deselect_point()
        self.update_status_bar()

    def deselect_point(self):
        self.table.selection_remove(self.table.selection())
        self.deselect_button.config(state=tk.DISABLED)
        self.delete_button.config(state=tk.DISABLED)
        self.smooth_button.config(state=tk.DISABLED)

    def on_table_select(self, event):
        selected_item = self.table.selection()
        if selected_item:
            self.selected_point = selected_item[0]
            self.deselect_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
            self.smooth_button.config(state=tk.NORMAL)

    def on_double_click(self, event):
        selected_item = self.table.selection()[0]
        column = self.table.identify_column(event.x)
        if column == '#1':  # Position column
            return  # Prevent changing positions 0 and 100
        elif column == '#2':  # Voltage column
            new_value = simpledialog.askfloat("Edit Voltage", "Enter new voltage (0-3):", parent=self.root)
            if new_value is not None:
                new_value = self.snap_to_grid(new_value, self.grid_y_interval)
                if new_value not in np.arange(0, 3.1, self.grid_y_interval):  # Check if the value is allowed by the grid
                    return
                self.update_table_value(selected_item, 1, new_value)

    def update_table_value(self, item, column, value):
        values = list(self.table.item(item, 'values'))
        values[column] = value
        self.table.item(item, values=values)
        self.point_list = [(float(self.table.item(i, 'values')[0]), float(self.table.item(i, 'values')[1])) for i in self.table.get_children()]
        self.update_plot()
        self.update_status_bar()

    def smooth_peak(self):
        if not self.selected_point:
            return
        selected_item = self.table.selection()[0]
        selected_index = self.table.index(selected_item)
        if selected_index in [0, len(self.table.get_children()) - 1]:
            return  # Do not smooth the first or last point

        points = np.array(self.point_list)
        x_points = points[:, 0]
        y_points = points[:, 1]

        prev_index = max(0, selected_index - 1)
        next_index = min(len(x_points) - 1, selected_index + 1)

        prev_x, prev_y = x_points[prev_index], y_points[prev_index]
        next_x, next_y = x_points[next_index], y_points[next_index]
        new_points = []

        if prev_index < selected_index:
            new_x_prev = np.linspace(prev_x, x_points[selected_index], 4)  # 4 points between the two existing points
            spline_prev = make_interp_spline([prev_x, x_points[selected_index], next_x], [prev_y, y_points[selected_index], next_y], k=2)
            new_y_prev = spline_prev(new_x_prev)
            new_points.extend(zip(new_x_prev[:-1], new_y_prev[:-1]))

        new_points.append((x_points[selected_index], y_points[selected_index]))

        if next_index > selected_index:
            new_x_next = np.linspace(x_points[selected_index], next_x, 4)[1:]  # 4 points between the two existing points
            new_y_next = spline_prev(new_x_next)
            new_points.extend(zip(new_x_next, new_y_next))

        self.point_list = self.point_list[:prev_index] + new_points + self.point_list[next_index + 1:]
        self.point_list = [(x, max(0, y)) for x, y in self.point_list]  # Ensure no points go below 0

        self.update_plot()
        self.update_table()
        self.update_status_bar()

    def update_plot(self):
        x, y = zip(*self.point_list) if self.point_list else ([], [])
        self.line.set_data(x, y)
        self.points.set_data(x, y)
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def update_table(self):
        for item in self.table.get_children():
            self.table.delete(item)
        for x, y in self.point_list:
            self.table.insert('', tk.END, values=(f"{x:.2f}", f"{y:.2f}"))
        self.update_status_bar()

    def interpolate_points(self):
        if not self.point_list:
            return []

        points = np.array(self.point_list)
        x_points = points[:, 0]
        y_points = points[:, 1]

        return list(zip(x_points, y_points))

    def copy_to_clipboard(self):
        interpolated_points = self.interpolate_points()
        hex_values = [f" 0x{int(y/3 * 0xFFF):03X}" for _, y in interpolated_points]
        hex_values.extend([" 0x000"] * (128 - len(hex_values)))  # Pad with 0x000 to make up 128 points

        # Format the output similar to CAL.INI
        formatted_hex = ""
        for i in range(0, len(hex_values), 10):
            formatted_hex += ", ".join(hex_values[i:i+10]) + ",\n"

        result = "USER_WAVEFORM = {\n" + formatted_hex.rstrip(",\n") + "\n}"
        pyperclip.copy(result)
        print(result)  # For debugging

    def generate_preset(self, waveform_type):
        resolution = simpledialog.askinteger("Resolution", "Enter number of points for the waveform (even numbers only):", minvalue=10, maxvalue=100, initialvalue=100)
        if resolution is None or resolution % 2 != 0:
            messagebox.showerror("Invalid Resolution", "Please enter an even number for the resolution.")
            return

        x = np.linspace(0, 100, resolution, endpoint=True)
        x = np.round(x).astype(int)  # Ensure positions are whole numbers

        if waveform_type == 'sine':
            midpoint = simpledialog.askfloat("Sine Wave", "Enter Midpoint Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=1.5, parent=self.root)
            if midpoint is None:
                return
            max_amplitude = simpledialog.askfloat("Sine Wave", "Enter Max. Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3, parent=self.root)
            if max_amplitude is None:
                return
            y = midpoint + (max_amplitude - midpoint) * np.sin(np.linspace(0, 2 * np.pi, resolution))
        elif waveform_type == 'sawtooth':
            start_amplitude = simpledialog.askfloat("Sawtooth Wave", "Enter Start Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=0, parent=self.root)
            if start_amplitude is None:
                return
            end_amplitude = simpledialog.askfloat("Sawtooth Wave", "Enter End Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3, parent=self.root)
            if end_amplitude is None:
                return
            y = np.linspace(start_amplitude, end_amplitude, resolution)
        elif waveform_type == 'triangle':
            min_amplitude = simpledialog.askfloat("Triangle Wave", "Enter Min. Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=0, parent=self.root)
            if min_amplitude is None:
                return
            max_amplitude = simpledialog.askfloat("Triangle Wave", "Enter Max. Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3, parent=self.root)
            if max_amplitude is None:
                return
            y = np.abs(np.mod(x / 50.0 + 1, 2) - 1) * (max_amplitude - min_amplitude) + min_amplitude
        elif waveform_type == 'square':
            low_amplitude = simpledialog.askfloat("Square Wave", "Enter Low Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=0, parent=self.root)
            if low_amplitude is None:
                return
            high_amplitude = simpledialog.askfloat("Square Wave", "Enter High Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3, parent=self.root)
            if high_amplitude is None:
                return
            y = np.where(np.mod(x, 20) < 10, low_amplitude, high_amplitude)

        self.point_list = list(zip(x, y))
        self.point_list[0] = (0, y[0])
        self.point_list[-1] = (100, y[-1])
        self.update_plot()
        self.update_table()
        self.update_status_bar()

    def change_resolution(self):
        resolution = simpledialog.askinteger("Resolution", "Enter new number of points for the waveform (even numbers only):", minvalue=10, maxvalue=100, initialvalue=len(self.point_list))
        if resolution is None or resolution % 2 != 0:
            messagebox.showerror("Invalid Resolution", "Please enter an even number for the resolution.")
            return

        points = np.array(self.point_list)
        x_points = points[:, 0]
        y_points = points[:, 1]

        new_x = np.linspace(0, 100, resolution, endpoint=True)
        new_x = np.round(new_x).astype(int)  # Ensure positions are whole numbers
        new_y = np.interp(new_x, x_points, y_points)

        self.point_list = list(zip(new_x, new_y))
        self.update_plot()
        self.update_table()
        self.update_status_bar()

    def load_waveform(self):
        load_window = tk.Toplevel(self.root)
        load_window.title("Load Waveform")

        text_field = ScrolledText(load_window, wrap=tk.WORD, width=60, height=10)
        text_field.pack(pady=10)

        def on_load():
            data = text_field.get("1.0", tk.END)
            try:
                self.point_list = self.parse_waveform_data(data)
                self.update_plot()
                self.update_table()
                load_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        load_button = tk.Button(load_window, text="Load", command=on_load)
        load_button.pack(side=tk.LEFT, padx=10, pady=10)

        cancel_button = tk.Button(load_window, text="Cancel", command=load_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=10, pady=10)

    def parse_waveform_data(self, data):
        start = data.find('{') + 1
        end = data.find('}')
        hex_values = data[start:end].split(',')
        points = []
        for i, hex_value in enumerate(hex_values):
            hex_value = hex_value.strip()
            if hex_value == '0x000' and len(points) >= 2:  # At least two points (0% and 100%) are required
                break  # Stop processing at the first padding point
            if hex_value:
                voltage = int(hex_value, 16) / 0xFFF * 3
                points.append((i, voltage))
        if points:
            # Adjust points to start at 0% and end at 100%
            positions = np.linspace(0, 100, len(points))
            points = [(positions[i], y) for i, (x, y) in enumerate(points)]
        return points

    def set_grid_x_interval(self, interval):
        self.grid_x_interval = interval
        self.update_grid()

    def set_grid_y_interval(self, interval):
        self.grid_y_interval = interval
        self.update_grid()

    def update_grid(self):
        self.ax.xaxis.set_major_locator(plt.MultipleLocator(self.grid_x_interval if self.grid_x_enabled.get() else 1000))
        self.ax.yaxis.set_major_locator(plt.MultipleLocator(self.grid_y_interval if self.grid_y_enabled.get() else 1000))
        self.ax.grid(which='both', linestyle='--', linewidth=0.5, color='lightgrey')
        self.canvas.draw()

    def clear_points(self):
        self.point_list = [(0, 1.5), (100, 1.5)]
        self.update_plot()
        self.update_table()
        self.update_status_bar()

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About this tool")
        tk.Label(about_window, text="Created by xyt6151").pack(pady=5)
        tk.Label(about_window, text="https://github.com/xyt6151/dt71_waveform_configurator").pack(pady=5)
        tk.Button(about_window, text="Close", command=about_window.destroy).pack(pady=10)
        about_window.geometry("300x150")
        about_window.transient(self.root)
        about_window.grab_set()
        self.root.wait_window(about_window)

    def update_status_bar(self):
        self.status_bar.config(text=f"Point count: {len(self.point_list)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WaveformGenerator(root)
    root.mainloop()
