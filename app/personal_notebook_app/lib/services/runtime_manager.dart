import 'dart:io';

class RuntimeCommandResult {
  final String command;
  final int exitCode;
  final String stdout;
  final String stderr;

  const RuntimeCommandResult({
    required this.command,
    required this.exitCode,
    required this.stdout,
    required this.stderr,
  });

  bool get ok => exitCode == 0;
  String get output {
    final parts = [stdout.trim(), stderr.trim()].where((p) => p.isNotEmpty).toList();
    return parts.isEmpty ? '(无输出)' : parts.join('\n');
  }
}

class RuntimeManager {
  bool get isSupportedDesktop => Platform.isMacOS || Platform.isWindows;

  Future<RuntimeCommandResult> dockerVersion() => _run('docker', const ['--version']);

  Future<RuntimeCommandResult> dockerComposeVersion() => _run('docker', const ['compose', 'version']);

  Future<RuntimeCommandResult> startCore() => _runCompose(const ['up', '-d']);

  Future<RuntimeCommandResult> stopCore() => _runCompose(const ['down']);

  Future<RuntimeCommandResult> restartCore() async {
    final down = await stopCore();
    if (!down.ok) return down;
    return startCore();
  }

  Future<RuntimeCommandResult> composePs() => _runCompose(const ['ps']);

  Future<RuntimeCommandResult> composeLogs() => _runCompose(const ['logs', '--tail=200']);

  Future<RuntimeCommandResult> _runCompose(List<String> args) async {
    final cwd = await _findComposeDirectory();
    return _run('docker', ['compose', ...args], workingDirectory: cwd.path);
  }

  Future<RuntimeCommandResult> _run(String executable, List<String> args, {String? workingDirectory}) async {
    final command = [executable, ...args].join(' ');
    try {
      final result = await Process.run(
        executable,
        args,
        workingDirectory: workingDirectory,
        runInShell: Platform.isWindows,
      );
      return RuntimeCommandResult(
        command: command,
        exitCode: result.exitCode,
        stdout: result.stdout?.toString() ?? '',
        stderr: result.stderr?.toString() ?? '',
      );
    } on ProcessException catch (e) {
      return RuntimeCommandResult(
        command: command,
        exitCode: e.errorCode,
        stdout: '',
        stderr: '无法执行 $command。请确认 Docker Desktop 已安装并启动。\n${e.message}',
      );
    } catch (e) {
      return RuntimeCommandResult(command: command, exitCode: 1, stdout: '', stderr: e.toString());
    }
  }

  Future<Directory> _findComposeDirectory() async {
    final envRoot = Platform.environment['PERSONAL_NOTEBOOK_ROOT'];
    if (envRoot != null && envRoot.isNotEmpty) {
      final infra = Directory('$envRoot/infra');
      if (await File('${infra.path}/docker-compose.yml').exists()) return infra;
      final root = Directory(envRoot);
      if (await File('${root.path}/docker-compose.yml').exists()) return root;
    }

    var dir = Directory.current;
    for (var i = 0; i < 10; i++) {
      final infra = Directory('${dir.path}/infra');
      if (await File('${infra.path}/docker-compose.yml').exists()) return infra;
      if (await File('${dir.path}/docker-compose.yml').exists()) return dir;
      final parent = dir.parent;
      if (parent.path == dir.path) break;
      dir = parent;
    }

    return Directory.current;
  }
}
