import 'package:flutter/material.dart';

import '../api/client.dart';

class DocumentDetailScreen extends StatefulWidget {
  final String? docId;

  const DocumentDetailScreen({super.key, this.docId});

  @override
  State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends State<DocumentDetailScreen> {
  final _docCtrl = TextEditingController();
  Map<String, dynamic>? _doc;
  Map<String, dynamic>? _qualityReport;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.docId != null && widget.docId!.isNotEmpty) {
      _docCtrl.text = widget.docId!;
      _load();
    }
  }

  @override
  void dispose() {
    _docCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final docId = _docCtrl.text.trim();
    if (docId.isEmpty) {
      setState(() => _error = '请先填写 Document ID');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final doc = await apiClient.get('/api/documents/$docId');
      if (mounted) {
        setState(() {
          _doc = doc;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _reindex() async {
    final docId = _docCtrl.text.trim();
    if (docId.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final resp = await apiClient.post('/api/documents/$docId/reindex');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Reindex 已提交：${resp['job_id'] ?? resp['message']}')),
      );
      await _load();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _loadQualityReport() async {
    final docId = _docCtrl.text.trim();
    if (docId.isEmpty) return;
    try {
      final report = await apiClient.get('/api/documents/$docId/quality-report');
      if (mounted) setState(() => _qualityReport = report);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_doc?['filename']?.toString() ?? '文档详情'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: _load)]),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _docCtrl,
            decoration: const InputDecoration(labelText: 'Document ID', border: OutlineInputBorder()),
            onSubmitted: (_) => _load(),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton.icon(onPressed: _loading ? null : _load, icon: const Icon(Icons.search), label: const Text('查看')),
              OutlinedButton.icon(onPressed: _loading ? null : _reindex, icon: const Icon(Icons.refresh), label: const Text('Reindex')),
              OutlinedButton.icon(onPressed: _loadQualityReport, icon: const Icon(Icons.fact_check), label: const Text('质量报告')),
            ],
          ),
          if (_loading) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          if (_doc != null) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _InfoRow('status', _doc!['status']?.toString() ?? ''),
                    _InfoRow('parse_status', _doc!['parse_status']?.toString() ?? ''),
                    _InfoRow('embed_status', _doc!['embed_status']?.toString() ?? ''),
                    _InfoRow('index_status', _doc!['index_status']?.toString() ?? ''),
                    _InfoRow('document_version', _doc!['document_version']?.toString() ?? ''),
                    _InfoRow('active_version', _doc!['active_version']?.toString() ?? ''),
                    _InfoRow('chunks', _doc!['chunk_count']?.toString() ?? '0'),
                    _InfoRow('assets', _doc!['asset_count']?.toString() ?? '0'),
                  ],
                ),
              ),
            ),
          ],
          if (_qualityReport != null) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: SelectableText(_qualityReport.toString()),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: SelectableText('$label: ${value.isEmpty ? '-' : value}'),
    );
  }
}
