import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

void main() {
  runApp(const ListenerApp());
}

class ListenerApp extends StatelessWidget {
  const ListenerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Jualan Listener',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0B7A75),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF3F8F7),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          isDense: true,
        ),
      ),
      home: const ListenerHomePage(),
    );
  }
}

class ListenerHomePage extends StatefulWidget {
  const ListenerHomePage({super.key});

  @override
  State<ListenerHomePage> createState() => _ListenerHomePageState();
}

class _ListenerHomePageState extends State<ListenerHomePage> {
  static const MethodChannel _channel = MethodChannel('jualan_listener/native');

  final TextEditingController _endpointController = TextEditingController();
  final TextEditingController _endpointSecondaryController = TextEditingController();
  final TextEditingController _secretController = TextEditingController();
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _amountController = TextEditingController(text: '50123');
  final TextEditingController _sourceAppController = TextEditingController(text: 'TEST_APP');
  final TextEditingController _referenceController = TextEditingController();
  final TextEditingController _rawTextController = TextEditingController(
    text: 'Pembayaran berhasil Rp50.123',
  );

  List<_InstalledApp> _apps = const [];
  Set<String> _selectedPackages = <String>{};
  bool _monitorAll = true;
  bool _listenerEnabled = false;
  bool _keepAliveForegroundEnabled = false;
  bool _appsLoaded = false;
  bool _appsLoading = false;
  int _pendingCount = 0;
  bool _isBusy = false;
  String _status = 'Siap';

  @override
  void initState() {
    super.initState();
    _loadInitial();
  }

  @override
  void dispose() {
    _endpointController.dispose();
    _endpointSecondaryController.dispose();
    _secretController.dispose();
    _searchController.dispose();
    _amountController.dispose();
    _sourceAppController.dispose();
    _referenceController.dispose();
    _rawTextController.dispose();
    super.dispose();
  }

  Future<void> _runBusy(Future<void> Function() action) async {
    if (mounted) {
      setState(() => _isBusy = true);
    }
    try {
      await action();
    } on PlatformException catch (e) {
      if (mounted) {
        setState(() {
          _status = e.message == null ? 'Terjadi error di operasi' : 'Error: ${e.message}';
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _status = 'Operasi gagal: $e';
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isBusy = false);
      }
    }
  }

  Future<void> _loadInitial() async {
    await _runBusy(() async {
      final configRaw = await _channel.invokeMethod<Map<Object?, Object?>>('getConfig');
      final selectedRaw = await _channel.invokeMethod<List<Object?>>('getSelectedApps');
      final listenerEnabledRaw = await _channel.invokeMethod<bool>('isListenerEnabled');
      final keepAliveRaw = await _channel.invokeMethod<bool>('isKeepAliveForegroundEnabled');
      final pendingRaw = await _channel.invokeMethod<int>('getPendingQueueCount');

      final config = configRaw ?? <Object?, Object?>{};
      if (mounted) {
        setState(() {
          _endpointController.text = (config['endpoint'] ?? '').toString();
          _endpointSecondaryController.text = (config['endpointSecondary'] ?? '').toString();
          _secretController.text = (config['secret'] ?? '').toString();
          _monitorAll = config['monitorAll'] == true;
          _selectedPackages = (selectedRaw ?? const <Object?>[])
              .map((e) => e.toString())
              .toSet();
          _listenerEnabled = listenerEnabledRaw ?? false;
          _keepAliveForegroundEnabled = keepAliveRaw ?? false;
          _pendingCount = pendingRaw ?? 0;
          _status = 'Konfigurasi dimuat';
        });
      }
    });
  }

  Future<void> _loadInstalledApps() async {
    if (_appsLoading) {
      return;
    }
    setState(() => _appsLoading = true);
    try {
      final appsRaw = await _channel.invokeMethod<List<Object?>>('getInstalledApps');
      final apps = (appsRaw ?? const <Object?>[])
          .map((raw) => _InstalledApp.fromMap((raw as Map).cast<Object?, Object?>()))
          .where((app) => app.packageName.isNotEmpty)
          .toList()
        ..sort((a, b) => a.label.toLowerCase().compareTo(b.label.toLowerCase()));

      if (!mounted) {
        return;
      }

      setState(() {
        _apps = apps;
        _appsLoaded = true;
        _status = 'Daftar aplikasi dimuat (${apps.length})';
      });
    } on PlatformException catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _status = 'Gagal load daftar app: ${e.message}';
      });
    } finally {
      if (mounted) {
        setState(() => _appsLoading = false);
      }
    }
  }

  Future<void> _loadAll() async {
    await _loadInitial();
    if (_appsLoaded) {
      await _loadInstalledApps();
    }
  }

  Future<void> _saveConfig() async {
    await _runBusy(() async {
      await _channel.invokeMethod('setConfig', {
        'endpoint': _endpointController.text.trim(),
        'endpointSecondary': _endpointSecondaryController.text.trim(),
        'secret': _secretController.text.trim(),
        'monitorAll': _monitorAll,
      });
      if (mounted) {
        setState(() {
          _status = 'Konfigurasi tersimpan';
        });
      }
      await _loadQueueCount();
    });
  }

  Future<void> _saveSelectedApps() async {
    try {
      await _channel.invokeMethod('setSelectedApps', {
        'packageNames': _selectedPackages.toList(),
      });
      setState(() {
        _status = 'Daftar aplikasi listener diperbarui';
      });
    } on PlatformException catch (e) {
      setState(() {
        _status = 'Gagal simpan daftar app: ${e.message}';
      });
    }
  }

  Future<void> _setKeepAliveForeground(bool enabled) async {
    await _runBusy(() async {
      await _channel.invokeMethod('setKeepAliveForegroundEnabled', {
        'enabled': enabled,
      });
      if (!mounted) return;
      setState(() {
        _keepAliveForegroundEnabled = enabled;
        _status = enabled
            ? 'Mode background aktif: notifikasi listener ditampilkan terus'
            : 'Mode background dimatikan';
      });
    });
  }

  Future<void> _lockToRecommendedApps() async {
    await _runBusy(() async {
      final selected = await _channel.invokeMethod<List<Object?>>('lockToRecommendedApps');
      if (!mounted) return;
      setState(() {
        _monitorAll = false;
        _selectedPackages = (selected ?? const <Object?>[])
            .map((e) => e.toString())
            .where((e) => e.isNotEmpty)
            .toSet();
        _status = 'Lock-in aktif: hanya DANA, ShopeePay, dan GoPay';
      });
    });
  }

  Future<void> _openSettings() async {
    await _channel.invokeMethod('openNotificationListenerSettings');
    await _refreshListenerStatus();
  }

  Future<void> _refreshListenerStatus() async {
    try {
      final enabled = await _channel.invokeMethod<bool>('isListenerEnabled');
      if (!mounted) return;
      setState(() {
        _listenerEnabled = enabled ?? false;
        _status = _listenerEnabled
            ? 'Notification listener aktif'
            : 'Notification listener belum aktif';
      });
    } on PlatformException catch (e) {
      if (!mounted) return;
      setState(() {
        _status = 'Gagal cek status listener: ${e.message}';
      });
    }
  }

  Future<void> _testConnection() async {
    await _runBusy(() async {
      final endpointPrimary = _endpointController.text.trim();
      final endpointSecondary = _endpointSecondaryController.text.trim();
      final secret = _secretController.text.trim();

      if (secret.isEmpty || (endpointPrimary.isEmpty && endpointSecondary.isEmpty)) {
        setState(() {
          _status = 'Endpoint/secret belum diatur';
        });
        return;
      }

      Future<String> testOne(String label, String endpoint) async {
        final response = await _channel.invokeMethod<Map<Object?, Object?>>(
          'testConnectionNative',
          {
            'endpoint': endpoint,
            'secret': secret,
          },
        );

        final ok = response?['ok'] == true;
        final code = response?['statusCode'];
        final body = response?['body'];
        final err = response?['error'];

        return ok
            ? '$label: sukses (HTTP $code)'
            : '$label: gagal (HTTP $code): ${err ?? body}';
      }

      final messages = <String>[];
      if (endpointPrimary.isNotEmpty) {
        messages.add(await testOne('Endpoint utama', endpointPrimary));
      }
      if (endpointSecondary.isNotEmpty) {
        messages.add(await testOne('Endpoint sekunder', endpointSecondary));
      }

      setState(() {
        _status = messages.join('\n');
      });
    });
  }

  Future<void> _sendTestPaymentPayload() async {
    final amount = int.tryParse(_amountController.text.trim()) ?? 0;
    if (amount <= 0) {
      setState(() {
        _status = 'Amount test harus angka > 0';
      });
      return;
    }

    await _runBusy(() async {
      await _channel.invokeMethod('enqueueTestPayload', {
        'amount': amount,
        'sourceApp': _sourceAppController.text.trim(),
        'reference': _referenceController.text.trim().isEmpty
            ? null
            : _referenceController.text.trim(),
        'rawText': _rawTextController.text.trim(),
      });
      await _channel.invokeMethod('enqueueFlush');
      await _loadQueueCount();
      setState(() {
        _status = 'Payload test dimasukkan ke queue dan dikirim';
      });
    });
  }

  Future<void> _loadQueueCount() async {
    try {
      final count = await _channel.invokeMethod<int>('getPendingQueueCount');
      if (!mounted) return;
      setState(() {
        _pendingCount = count ?? 0;
      });
    } on PlatformException catch (e) {
      if (!mounted) return;
      setState(() {
        _status = 'Gagal membaca queue: ${e.message}';
      });
    }
  }

  Future<void> _flushQueue() async {
    await _runBusy(() async {
      await _channel.invokeMethod('enqueueFlush');
      await _loadQueueCount();
      if (mounted) {
        setState(() {
          _status = 'Flush queue dijalankan';
        });
      }
    });
  }

  Future<void> _refreshEverything() async {
    await _loadInitial();
    if (_appsLoaded) {
      await _loadInstalledApps();
    }
  }

  Widget _sectionCard({
    required String title,
    required IconData icon,
    required Widget child,
  }) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 20),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 10),
            child,
          ],
        ),
      ),
    );
  }

  Widget _buildStatusCard() {
    final activeColor = _listenerEnabled ? const Color(0xFF127A43) : const Color(0xFFB22727);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          colors: _listenerEnabled
              ? const [Color(0xFFDCF8E9), Color(0xFFEAFBF2)]
              : const [Color(0xFFFFECE9), Color(0xFFFFF4F2)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        border: Border.all(color: activeColor.withValues(alpha: 0.28)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _listenerEnabled ? Icons.check_circle : Icons.warning_amber_rounded,
                color: activeColor,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _listenerEnabled ? 'Listener aktif dan siap menerima notifikasi' : 'Listener belum aktif',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: activeColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          AnimatedSwitcher(
            duration: const Duration(milliseconds: 220),
            child: Text(
              'Pending queue: $_pendingCount event',
              key: ValueKey<int>(_pendingCount),
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _keepAliveForegroundEnabled
                ? 'Mode background: notifikasi "Mendengarkan notifikasi pembayaran..." aktif'
                : 'Mode background: nonaktif',
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(
                onPressed: _openSettings,
                icon: const Icon(Icons.notifications_active_outlined),
                label: const Text('Aktifkan Listener'),
              ),
              OutlinedButton(
                onPressed: _refreshListenerStatus,
                child: const Text('Cek Status'),
              ),
              OutlinedButton(
                onPressed: _flushQueue,
                child: const Text('Flush Queue'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAppSelectionCard(List<_InstalledApp> filteredApps) {
    return _sectionCard(
      title: 'Aplikasi Yang Didengarkan',
      icon: Icons.apps_rounded,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SwitchListTile(
            value: _keepAliveForegroundEnabled,
            onChanged: (value) => _setKeepAliveForeground(value),
            contentPadding: EdgeInsets.zero,
            title: const Text('Notifikasi background tetap aktif'),
            subtitle: const Text('Tampilkan notifikasi "mendengarkan notifikasi..." di notification center'),
          ),
          const SizedBox(height: 6),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.tonalIcon(
              onPressed: _lockToRecommendedApps,
              icon: const Icon(Icons.lock_outline),
              label: const Text('Lock-in DANA + ShopeePay + GoPay'),
            ),
          ),
          const SizedBox(height: 6),
          SwitchListTile(
            value: _monitorAll,
            onChanged: (value) {
              setState(() {
                _monitorAll = value;
              });
            },
            contentPadding: EdgeInsets.zero,
            title: const Text('Dengarkan semua aplikasi'),
          ),
          const SizedBox(height: 4),
          if (!_appsLoaded)
            FilledButton.icon(
              onPressed: _appsLoading ? null : _loadInstalledApps,
              icon: _appsLoading
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.download_rounded),
              label: Text(_appsLoading ? 'Memuat daftar aplikasi...' : 'Muat daftar aplikasi terpasang'),
            )
          else ...[
            TextField(
              controller: _searchController,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                hintText: 'Cari nama/package aplikasi',
              ),
            ),
            const SizedBox(height: 8),
            if (_monitorAll)
              const Text('Mode semua aplikasi aktif, pilihan per-app dinonaktifkan.'),
            const SizedBox(height: 8),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              child: _appsLoading
                  ? const SizedBox(
                      key: ValueKey<String>('apps-loading'),
                      height: 120,
                      child: Center(child: CircularProgressIndicator()),
                    )
                  : SizedBox(
                      key: const ValueKey<String>('apps-list'),
                      height: 280,
                      child: filteredApps.isEmpty
                          ? const Center(
                              child: Text('Tidak ada app yang cocok dengan pencarian.'),
                            )
                          : ListView.builder(
                              itemCount: filteredApps.length,
                              itemBuilder: (context, index) {
                                final app = filteredApps[index];
                                final checked = _selectedPackages.contains(app.packageName);
                                return CheckboxListTile(
                                  value: checked,
                                  onChanged: _monitorAll
                                      ? null
                                      : (value) {
                                          setState(() {
                                            if (value == true) {
                                              _selectedPackages.add(app.packageName);
                                            } else {
                                              _selectedPackages.remove(app.packageName);
                                            }
                                          });
                                        },
                                  title: Text(app.label),
                                  subtitle: Text(app.packageName),
                                  dense: true,
                                  controlAffinity: ListTileControlAffinity.leading,
                                );
                              },
                            ),
                    ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(
                  onPressed: _monitorAll ? null : _saveSelectedApps,
                  child: const Text('Simpan Pilihan Aplikasi'),
                ),
                TextButton(
                  onPressed: _loadInstalledApps,
                  child: const Text('Muat Ulang Daftar App'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final query = _searchController.text.trim().toLowerCase();
    final filteredApps = _apps
        .where((app) {
          if (query.isEmpty) return true;
          return app.label.toLowerCase().contains(query) ||
              app.packageName.toLowerCase().contains(query);
        })
        .toList();

    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Jualan Notification Listener'),
            Text(
              'Bridge notifikasi pembayaran',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.normal),
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _isBusy ? null : _loadAll,
            icon: const Icon(Icons.refresh),
          )
        ],
      ),
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFFE8F3F2), Color(0xFFF6FBFA)],
              ),
            ),
          ),
          RefreshIndicator(
            onRefresh: _refreshEverything,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _buildStatusCard(),
                const SizedBox(height: 12),
                _sectionCard(
                  title: 'Konfigurasi Endpoint',
                  icon: Icons.link,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: _endpointController,
                        decoration: const InputDecoration(
                          labelText: 'Endpoint payment',
                          hintText: 'https://domain/listener/payment',
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _endpointSecondaryController,
                        decoration: const InputDecoration(
                          labelText: 'Endpoint payment (sekunder)',
                          hintText: 'https://domain-2/listener/payment',
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _secretController,
                        decoration: const InputDecoration(labelText: 'Shared secret'),
                      ),
                      const SizedBox(height: 10),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          FilledButton(
                            onPressed: _saveConfig,
                            child: const Text('Simpan Config'),
                          ),
                          OutlinedButton(
                            onPressed: _testConnection,
                            child: const Text('Test Koneksi'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                _buildAppSelectionCard(filteredApps),
                const SizedBox(height: 12),
                _sectionCard(
                  title: 'Test Kirim Payload Payment',
                  icon: Icons.science_outlined,
                  child: ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: const Text('Buka panel test payload'),
                    subtitle: const Text('Panel ini untuk simulasi dari Android listener'),
                    childrenPadding: const EdgeInsets.only(bottom: 8),
                    children: [
                      TextField(
                        controller: _amountController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(labelText: 'Amount (Rp)'),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _sourceAppController,
                        decoration: const InputDecoration(labelText: 'Source app'),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _referenceController,
                        decoration: const InputDecoration(
                          labelText: 'Reference (opsional)',
                          hintText: 'PAY-ORD...',
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _rawTextController,
                        minLines: 2,
                        maxLines: 5,
                        decoration: const InputDecoration(labelText: 'Raw text notifikasi'),
                      ),
                      const SizedBox(height: 10),
                      FilledButton(
                        onPressed: _sendTestPaymentPayload,
                        child: const Text('Kirim Payload Test'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 220),
                  child: Text(
                    'Status: $_status',
                    key: ValueKey<String>(_status),
                  ),
                ),
              ],
            ),
          ),
          if (_isBusy)
            Positioned.fill(
              child: IgnorePointer(
                child: AnimatedOpacity(
                  duration: const Duration(milliseconds: 180),
                  opacity: _isBusy ? 1 : 0,
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.08),
                    alignment: Alignment.center,
                    child: const CircularProgressIndicator(),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _InstalledApp {
  final String packageName;
  final String label;

  const _InstalledApp({required this.packageName, required this.label});

  factory _InstalledApp.fromMap(Map<Object?, Object?> map) {
    return _InstalledApp(
      packageName: (map['packageName'] ?? '').toString(),
      label: (map['label'] ?? '').toString(),
    );
  }
}
