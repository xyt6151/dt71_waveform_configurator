import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
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
        self.ax.set_xlabel('Percentage')
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
        
        self.table.bind("<ButtonRelease-1>", self.on_table_select)
        self.table.bind("<Double-1>", self.on_double_click)
        self.update_plot()
        self.update_table()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        x, y = event.xdata, event.ydata
        if event.button == 1:
            self.add_or_update_point(x, y)
        elif event.button == 3:
            self.delete_point_by_position(x, y)
        self.update_plot()
        self.update_table()
        
    def add_or_update_point(self, x, y):
        if x < 1:  # If close to 0%, update 0% point
            x = 0
        elif x > 99:  # If close to 100%, update 100% point
            x = 100

        for i, (px, py) in enumerate(self.point_list):
            if px == x or (px == 0 and x == 100) or (px == 100 and x == 0):
                self.point_list[i] = (x, y)
                if x == 0:
                    self.point_list[self.point_list.index((100, py))] = (100, y)
                elif x == 100:
                    self.point_list[self.point_list.index((0, py))] = (0, y)
                break
        else:
            self.point_list.append((x, y))

        self.point_list.sort()
        
    def delete_point_by_position(self, x, y):
        tolerance = 2
        self.point_list = [(px, py) for (px, py) in self.point_list if abs(px - x) > tolerance or abs(py - y) > tolerance]
        
        # Ensure points at 0% and 100% are present
        if (0, 1.5) not in self.point_list:
            self.point_list.append((0, 1.5))
        if (100, 1.5) not in self.point_list:
            self.point_list.append((100, 1.5))

        self.point_list.sort()
        
    def delete_point(self):
        selected_item = self.table.selection()[0]
        position = float(self.table.item(selected_item, "values")[0])
        if position in [0, 100]:
            return  # Prevent deletion of 0% and 100% points
        
        self.point_list = [(x, y) for (x, y) in self.point_list if x != position]
        
        self.update_plot()
        self.update_table()
        self.deselect_point()

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
            new_value = simpledialog.askfloat("Edit Position", "Enter new position (0-100):")
            if new_value is not None:
                self.update_table_value(selected_item, 0, new_value)
        elif column == '#2':  # Voltage column
            new_value = simpledialog.askfloat("Edit Voltage", "Enter new voltage (0-3):")
            if new_value is not None:
                self.update_table_value(selected_item, 1, new_value)

    def update_table_value(self, item, column, value):
        values = list(self.table.item(item, 'values'))
        values[column] = value
        self.table.item(item, values=values)
        self.point_list = [(float(self.table.item(i, 'values')[0]), float(self.table.item(i, 'values')[1])) for i in self.table.get_children()]
        self.update_plot()
        
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
        
        # Create additional points around the selected point
        new_points = []
        if selected_index > 0 and selected_index < len(x_points) - 1:
            prev_x, prev_y = x_points[selected_index - 1], y_points[selected_index - 1]
            next_x, next_y = x_points[selected_index + 1], y_points[selected_index + 1]
            new_x = np.linspace(prev_x, next_x, 5)  # 5 points between the two existing points
            spline = make_interp_spline([prev_x, x_points[selected_index], next_x], [prev_y, y_points[selected_index], next_y], k=2)
            new_y = spline(new_x)
            new_points = list(zip(new_x, new_y))

        # Replace the old points with the new points, ensuring we do not exceed 100 points
        self.point_list = self.point_list[:selected_index - 1] + new_points + self.point_list[selected_index + 2:]
        self.point_list = [(x, max(0, y)) for x, y in self.point_list]  # Ensure no points go below 0
        
        self.update_plot()
        self.update_table()
        
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
            
    def interpolate_points(self):
        if not self.point_list:
            return []
        
        points = np.array(self.point_list)
        x_points = points[:, 0]
        y_points = points[:, 1]

        interpolated_x = np.linspace(0, 100, 100)
        interpolated_y = np.interp(interpolated_x, x_points, y_points)
        
        return list(zip(interpolated_x, interpolated_y))

    def copy_to_clipboard(self):
        interpolated_points = self.interpolate_points()
        hex_values = [f"0x{int(y/3 * 0xFFF):03X}" for _, y in interpolated_points]
        hex_values.extend(["0x000"] * 28)  # Append 28 points of 0x000
        result = "USER_WAVEFORM = {" + ", ".join(hex_values) + ", }"
        pyperclip.copy(result)
        print(result)  # For debugging

    def generate_preset(self, waveform_type):
        if waveform_type == 'sine':
            midpoint = simpledialog.askfloat("Sine Wave", "Enter Midpoint Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=1.5)
            max_amplitude = simpledialog.askfloat("Sine Wave", "Enter Max. Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3)
            if midpoint is None or max_amplitude is None:
                return
            x = np.linspace(0, 100, 100)
            y = midpoint + (max_amplitude - midpoint) * np.sin(np.linspace(0, 2 * np.pi, 100))
        elif waveform_type == 'sawtooth':
            start_amplitude = simpledialog.askfloat("Sawtooth Wave", "Enter Start Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=0)
            end_amplitude = simpledialog.askfloat("Sawtooth Wave", "Enter End Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3)
            if start_amplitude is None or end_amplitude is None:
                return
            x = np.linspace(0, 100, 100)
            y = np.linspace(start_amplitude, end_amplitude, 100)
        elif waveform_type == 'triangle':
            min_amplitude = simpledialog.askfloat("Triangle Wave", "Enter Min. Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=0)
            max_amplitude = simpledialog.askfloat("Triangle Wave", "Enter Max. Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3)
            if min_amplitude is None or max_amplitude is None:
                return
            x = np.linspace(0, 100, 100)
            y = np.abs(np.mod(x / 50.0 + 1, 2) - 1) * (max_amplitude - min_amplitude) + min_amplitude
        elif waveform_type == 'square':
            low_amplitude = simpledialog.askfloat("Square Wave", "Enter Low Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=0)
            high_amplitude = simpledialog.askfloat("Square Wave", "Enter High Amplitude (0-3):", minvalue=0, maxvalue=3, initialvalue=3)
            if low_amplitude is None or high_amplitude is None:
                return
            x = np.linspace(0, 100, 100)
            y = np.where(np.mod(x, 20) < 10, low_amplitude, high_amplitude)
        
        self.point_list = list(zip(x, y))
        self.point_list[0] = (0, y[0])
        self.point_list[-1] = (100, y[-1])
        self.update_plot()
        self.update_table()

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

if __name__ == "__main__":
    root = tk.Tk()
    app = WaveformGenerator(root)
    root.mainloop()
