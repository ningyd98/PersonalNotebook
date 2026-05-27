import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../api/client.dart';
import 'document_detail_screen.dart';
import 'document_list_screen.dart';

class DocumentUploadScreen extends StatefulWidget {
  final String? kbId;

  const DocumentUploadScreen({super.key, this.kbId});

  @override
  State<DocumentUploadScreen> createState() => _DocumentUploadScreenState();
}

class _DocumentUploadScreenState extends State<DocumentUploadScreen> {
  final _kbCtrl = TextEditingController();
  bool _loading = false;
  Map<String, dynamic>? _result;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.kbId != null && widget.kbId!.isNotEmpty) {
      _kbCtrl.text = widget.kbId!;
    }
  }

  @override
  void dispose() {
    _kbCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickAndUpload() async {
    final kbId = _kbCtrl.text.trim();
    if (kbId.isEmpty) {
      setState(() => _error = '请先填写 KB ID');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    try {
      final picked = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: const ['md', 'txt', 'pdf'],
        allowMultiple: false,
        withData: false,
      );
      if (picked == null || picked.files.isEmpty) {
        if (mounted) setState(() => _loading = false);
        return;
      }

      final filePath = picked.files.single.path;
      if (filePath == null || filePath.isEmpty) {
        throw ApiException('当前平台没有返回可上传的本地文件路径', 0);
      }

      final resp = await apiClient.upload('/api/kbs/$kbId/documents/upload', filePath);
      if (!mounted) return;
      setState(() {
        _result = resp;
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final documentId = _result?['document_id']?.toString();
    return Scaffold(
      appBar: AppBar(title: const Text('上传文档')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          TextField(
            controller: _kbCtrl,
            decoration: const InputDecoration(labelText: 'KB ID', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _loading ? null : _pickAndUpload,
            icon: const Icon(Icons.upload_file),
            label: Text(_loading ? '上传中...' : '选择 .md / .txt / .pdf 文件'),
          ),
          if (_loading) const Padding(padding: EdgeInsets.only(top: 12), child: LinearProgressIndicator()),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          if (_result != null) ...[
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('上传结果', style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    _InfoRow('document_id', documentId ?? ''),
                    _InfoRow('job_id', _result?['job_id']?.toString() ?? ''),
                    _InfoRow('duplicate', _result?['duplicate']?.toString() ?? 'false'),
                    _InfoRow('parse_status', _result?['parse_status']?.toString() ?? ''),
                    _InfoRow('message', _result?['message']?.toString() ?? ''),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton.icon(
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => DocumentListScreen(kbId: _kbCtrl.text.trim())),
                  ),
                  icon: const Icon(Icons.list),
                  label: const Text('文档列表'),
                ),
                if (documentId != null && documentId.isNotEmpty)
                  FilledButton.icon(
                    onPressed: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => DocumentDetailScreen(docId: documentId)),
                    ),
                    icon: const Icon(Icons.description),
                    label: const Text('文档详情'),
                  ),
              ],
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
