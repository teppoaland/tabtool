using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

internal static class Program
{
    private static string baseDir;
    private static string python;
    private static string dataDir;
    private static string portFile;
    private static string logFile;
    private static Process server;
    private static NotifyIcon tray;
    private static ContextMenuStrip menu;
    private static Form syncForm;
    private static string releaseUrl;
    private static string releaseTag;
    private static int port;
    private static bool exiting;

    private const string ReleasesPage = "https://github.com/teppoaland/tabtool/releases/latest";
    private const string ReleasesApi = "https://api.github.com/repos/teppoaland/tabtool/releases?per_page=100";

    [STAThread]
    private static void Main()
    {
        bool created;
        using (var mutex = new Mutex(true, "Local\\PianoCaptureLauncher", out created))
        {
            if (!created)
            {
                OpenRunning();
                return;
            }

            baseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            python = Path.Combine(baseDir, "runtime", "python.exe");
            string root = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "PianoCapture"
            );
            dataDir = Path.Combine(root, "data_piano");
            portFile = Path.Combine(root, "port.txt");
            logFile = Path.Combine(root, "logs", "server.log");
            Directory.CreateDirectory(root);
            Directory.CreateDirectory(dataDir);
            Directory.CreateDirectory(Path.Combine(root, "logs"));

            if (!File.Exists(python))
            {
                MessageBox.Show(
                    "PianoCapture -asennus on puutteellinen: runtime\\python.exe puuttuu.",
                    "PianoCapture",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            port = FindFreePort(8020);
            StartServer();
            if (!WaitForServer(90))
            {
                MessageBox.Show(
                    "PianoCapture -palvelin ei käynnistynyt. Lokitiedosto:\n" + logFile,
                    "PianoCapture",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                KillServer();
                return;
            }

            try { File.WriteAllText(portFile, port.ToString()); } catch { }
            OpenBrowser();

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            Icon icon;
            try { icon = new Icon(Path.Combine(baseDir, "piano.ico")); }
            catch { icon = SystemIcons.Application; }

            menu = new ContextMenuStrip();
            menu.Items.Add("Avaa PianoCapture", null, delegate { OpenBrowser(); });
            menu.Items.Add("Tarkista päivitykset", null, delegate { OpenPage(ReleasesPage); });
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Lopeta", null, delegate { ExitApp(); });

            tray = new NotifyIcon();
            tray.Icon = icon;
            tray.Text = "PianoCapture";
            tray.Visible = true;
            tray.ContextMenuStrip = menu;
            tray.DoubleClick += delegate { OpenBrowser(); };
            tray.BalloonTipClicked += delegate { OfferUpdate(); };
            tray.ShowBalloonTip(
                3000,
                "PianoCapture",
                "Käynnissä. Kaksoisklikkaa kuvaketta tai valitse Lopeta.",
                ToolTipIcon.Info
            );

            syncForm = new Form();
            syncForm.ShowInTaskbar = false;
            IntPtr hidden = syncForm.Handle;
            var updateCheck = new Thread(CheckForUpdates);
            updateCheck.IsBackground = true;
            updateCheck.Start();

            Application.Run(new ApplicationContext());
        }
    }

    private static void CheckForUpdates()
    {
        try
        {
            Thread.Sleep(2500);
            ServicePointManager.SecurityProtocol |= SecurityProtocolType.Tls12;
            var request = (HttpWebRequest)WebRequest.Create(ReleasesApi);
            request.UserAgent = "PianoCapture-Windows";
            request.Accept = "application/vnd.github+json";
            request.Timeout = 8000;
            request.Proxy = null;

            string body;
            using (var response = (HttpWebResponse)request.GetResponse())
            using (var reader = new StreamReader(response.GetResponseStream()))
            {
                body = reader.ReadToEnd();
            }

            string local = LocalVersion();
            MatchCollection tags = Regex.Matches(body, "\"tag_name\"\\s*:\\s*\"([^\"]+)\"");
            for (int i = 0; i < tags.Count; i++)
            {
                int start = tags[i].Index;
                int end = i + 1 < tags.Count ? tags[i + 1].Index : body.Length;
                string chunk = body.Substring(start, end - start);
                if (chunk.IndexOf("PianoCapture-Setup", StringComparison.OrdinalIgnoreCase) < 0)
                {
                    continue;
                }

                string tag = tags[i].Groups[1].Value;
                if (CompareVersions(tag.TrimStart('v', 'V'), local) <= 0)
                {
                    return;
                }

                releaseTag = tag;
                releaseUrl = "https://github.com/teppoaland/tabtool/releases/tag/" + tag;
                PostUpdate(tag, local);
                return;
            }
        }
        catch { }
    }

    private static string LocalVersion()
    {
        try
        {
            string file = Path.Combine(baseDir, "runtime", "app", "piano", "__init__.py");
            foreach (string line in File.ReadAllLines(file))
            {
                string text = line.Trim();
                if (!text.StartsWith("__version__")) continue;
                int first = text.IndexOf('"');
                int last = text.LastIndexOf('"');
                if (first >= 0 && last > first) return text.Substring(first + 1, last - first - 1).Trim();
            }
        }
        catch { }
        return "0.0";
    }

    private static int CompareVersions(string left, string right)
    {
        string[] a = left.Split('.');
        string[] b = right.Split('.');
        int count = Math.Max(a.Length, b.Length);
        for (int i = 0; i < count; i++)
        {
            int x, y;
            int.TryParse(i < a.Length ? a[i] : "0", out x);
            int.TryParse(i < b.Length ? b[i] : "0", out y);
            if (x != y) return x.CompareTo(y);
        }
        return 0;
    }

    private static void PostUpdate(string tag, string local)
    {
        try
        {
            syncForm.BeginInvoke(new Action(delegate { ShowUpdate(tag, local); }));
        }
        catch { }
    }

    private static void ShowUpdate(string tag, string local)
    {
        if (releaseTag != tag) return;
        var item = new ToolStripMenuItem("Päivitys saatavilla: " + tag + " – avaa lataussivu");
        item.Click += delegate { OfferUpdate(); };
        menu.Items.Insert(0, item);
        menu.Items.Insert(1, new ToolStripSeparator());
        tray.Text = "PianoCapture – päivitys saatavilla";
        tray.ShowBalloonTip(
            10000,
            "PianoCapture – päivitys saatavilla",
            "Uusi versio " + tag + " (asennettu " + local + "). Klikkaa tästä päivittääksesi.",
            ToolTipIcon.Info
        );
    }

    private static void OfferUpdate()
    {
        if (string.IsNullOrEmpty(releaseUrl)) return;
        var answer = MessageBox.Show(
            "Uusi PianoCapture-versio " + releaseTag + " on saatavilla (asennettu " + LocalVersion() + ").\n\n"
                + "Lataussivu avataan selaimessa. Asenna uusi versio vanhan päälle – data säilyy.\n\n"
                + "Avataanko lataussivu nyt?",
            "PianoCapture – päivitys saatavilla",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Information
        );
        if (answer == DialogResult.Yes) OpenPage(releaseUrl);
    }

    private static void OpenPage(string url)
    {
        try
        {
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        }
        catch { }
    }

    private static int FindFreePort(int start)
    {
        for (int candidate = start; candidate < start + 50; candidate++)
        {
            try
            {
                var listener = new TcpListener(IPAddress.Any, candidate);
                listener.Start();
                listener.Stop();
                return candidate;
            }
            catch (SocketException) { }
        }
        return start;
    }

    private static void StartServer()
    {
        var info = new ProcessStartInfo();
        info.FileName = python;
        info.Arguments = "-m uvicorn piano.main:app --host 0.0.0.0 --port " + port;
        info.WorkingDirectory = Path.Combine(baseDir, "runtime");
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        info.EnvironmentVariables["PIANO_DATA_DIR"] = dataDir;
        info.EnvironmentVariables["PIANO_HOST"] = "0.0.0.0";
        info.EnvironmentVariables["PIANO_PORT"] = port.ToString();
        info.EnvironmentVariables["PYTHONUTF8"] = "1";
        info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";

        string ffmpeg = Path.Combine(baseDir, "runtime", "ffmpeg", "bin");
        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        info.EnvironmentVariables["PATH"] = ffmpeg + ";" + path;

        server = new Process();
        server.StartInfo = info;
        server.EnableRaisingEvents = true;
        server.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e) { Log(e.Data); };
        server.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { Log(e.Data); };
        server.Exited += delegate
        {
            if (!exiting) Log("server exited with code " + server.ExitCode);
        };
        server.Start();
        server.BeginOutputReadLine();
        server.BeginErrorReadLine();
    }

    private static void Log(string line)
    {
        if (line == null) return;
        try
        {
            lock (typeof(Program))
            {
                File.AppendAllText(
                    logFile,
                    DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss ") + line + Environment.NewLine
                );
            }
        }
        catch { }
    }

    private static bool WaitForServer(int seconds)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(seconds);
        while (DateTime.UtcNow < deadline)
        {
            if (server == null || server.HasExited) return false;
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(
                    "http://127.0.0.1:" + port + "/api/piano/health"
                );
                request.Timeout = 800;
                request.Proxy = null;
                using (var response = (HttpWebResponse)request.GetResponse())
                {
                    if ((int)response.StatusCode == 200) return true;
                }
            }
            catch { }
            Thread.Sleep(500);
        }
        return false;
    }

    private static void OpenBrowser()
    {
        try
        {
            Process.Start(new ProcessStartInfo("http://127.0.0.1:" + port)
            {
                UseShellExecute = true
            });
        }
        catch { }
    }

    private static void OpenRunning()
    {
        try
        {
            string root = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "PianoCapture"
            );
            string file = Path.Combine(root, "port.txt");
            if (File.Exists(file))
            {
                int runningPort;
                if (int.TryParse(File.ReadAllText(file).Trim(), out runningPort))
                {
                    Process.Start(new ProcessStartInfo("http://127.0.0.1:" + runningPort)
                    {
                        UseShellExecute = true
                    });
                    return;
                }
            }
        }
        catch { }
        MessageBox.Show(
            "PianoCapture on jo käynnissä. Avaa se tehtäväpalkin ilmaisinalueen kuvakkeesta.",
            "PianoCapture",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        );
    }

    private static void ExitApp()
    {
        exiting = true;
        KillServer();
        try { File.Delete(portFile); } catch { }
        if (tray != null)
        {
            tray.Visible = false;
            tray.Dispose();
        }
        Application.Exit();
    }

    private static void KillServer()
    {
        try
        {
            if (server != null && !server.HasExited)
            {
                var info = new ProcessStartInfo("taskkill", "/PID " + server.Id + " /T /F");
                info.UseShellExecute = false;
                info.CreateNoWindow = true;
                Process.Start(info);
                server.WaitForExit(5000);
            }
        }
        catch { }
    }
}
