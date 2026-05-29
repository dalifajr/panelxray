@extends('layouts.app')

@push('styles')
<style>
.btn-group {
    position: relative;
    display: inline-flex;
    vertical-align: middle;
}

.btn-group-sm > .btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.875rem;
    border-radius: 0.375rem;
}

.table .btn {
    display: inline-block;
    font-weight: 500;
    line-height: 1.5;
    color: #4a5568;
    text-align: center;
    vertical-align: middle;
    cursor: pointer;
    user-select: none;
    background-color: #f8f9fa;
    border: 0.8px solid #e2e8f0;
    padding: 9.6px 19.2px;
    font-size: 12px;
    border-radius: 10px;
    transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.table .btn-group > .btn:first-child {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
    border-top-left-radius: 10px;
    border-bottom-left-radius: 10px;
}

.table .btn-group > .btn:not(:first-child):not(:last-child) {
    border-radius: 0;
}

.table .btn-group > .btn:last-child {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}

.table .btn-outline-success:hover {
    color: #fff;
    background-color: #198754;
    border-color: #198754;
}

.table .btn-outline-danger:hover {
    color: #fff;
    background-color: #dc3545;
    border-color: #dc3545;
}

.table .text-end {
    text-align: right !important;
}

.table .pe-3 {
    padding-right: 1rem !important;
}

.table .py-2 {
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
}

.table td {
    vertical-align: middle;
}
</style>
@endpush

@section('content')
<div class="container-fluid py-4">
    <div class="row mb-4">
        <div class="col-12">
            <h2 class="fw-bold text-dark mb-0">Daftar Pesanan</h2>
            <p class="text-secondary">Kelola semua pesanan Topup dan Pembuatan/Perpanjangan VPN.</p>
        </div>
    </div>

    @if(session('sweet_success'))
    <div class="alert alert-success alert-dismissible fade show shadow-sm" role="alert">
        <i class="fas fa-check-circle me-2"></i>{{ session('sweet_success') }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    @endif
    @if(session('sweet_error'))
    <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
        <i class="fas fa-exclamation-circle me-2"></i>{{ session('sweet_error') }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
    @endif

    <div class="card shadow-sm border-0 mb-4">
        <div class="card-body">
            <form action="{{ route('admin.orders') }}" method="GET" class="row g-2 mb-4">
                <div class="col-md-5">
                    <input type="text" name="search" class="form-control" placeholder="Cari Ref, Deskripsi, atau Username User..." value="{{ $search }}">
                </div>
                <div class="col-md-4">
                    <select name="status" class="form-select">
                        <option value="all" {{ $status == 'all' ? 'selected' : '' }}>Semua Status</option>
                        <option value="pending" {{ $status == 'pending' ? 'selected' : '' }}>Pending</option>
                        <option value="success" {{ $status == 'success' ? 'selected' : '' }}>Sukses</option>
                        <option value="cancelled" {{ $status == 'cancelled' ? 'selected' : '' }}>Dibatalkan</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <button type="submit" class="btn btn-primary w-100"><i class="fas fa-search me-1"></i> Filter</button>
                </div>
            </form>

            <div class="table-responsive">
                <table class="table table-hover table-sm align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Waktu</th>
                            <th>Reference</th>
                            <th>User</th>
                            <th>Tipe</th>
                            <th>Deskripsi</th>
                            <th>Total Tagihan</th>
                            <th>Status</th>
                            <th>Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($orders as $order)
                        @php
                            $meta = is_string($order->metadata) ? json_decode($order->metadata, true) : $order->metadata;
                        @endphp
                        <tr>
                            <td>{{ $order->created_at ? $order->created_at->format('d M Y H:i') : '-' }}</td>
                            <td><span class="badge bg-light text-dark border">{{ $order->reference }}</span></td>
                            <td>{{ $order->user?->username ?? $order->user?->name ?? 'Unknown' }}</td>
                            <td>
                                @if($order->type == 'topup')
                                    <span class="badge bg-info">Top Up</span>
                                @elseif($order->type == 'vpn_purchase' || $order->type == 'vpn_purchase_qris')
                                    <span class="badge bg-primary">Beli VPN</span>
                                @elseif($order->type == 'vpn_renew_qris')
                                    <span class="badge bg-primary">Perpanjang VPN</span>
                                @else
                                    <span class="badge bg-secondary">{{ $order->type }}</span>
                                @endif
                            </td>
                            <td>
                                {{ $order->description }}
                                @if($order->status === 'cancelled' && isset($meta['cancel_reason']))
                                    <br><small class="text-danger">Alasan batal: {{ $meta['cancel_reason'] }}</small>
                                @endif
                            </td>
                            <td class="fw-bold text-dark">Rp {{ number_format($order->total_amount, 0, ',', '.') }}</td>
                            <td>
                                @if($order->status == 'success')
                                    <span class="badge bg-success">Sukses</span>
                                @elseif($order->status == 'pending')
                                    <span class="badge bg-warning text-dark">Pending</span>
                                @else
                                    <span class="badge bg-danger">Dibatalkan</span>
                                @endif
                            </td>
                            <td>
                                @if($order->status === 'pending')
                                    <div class="btn-group btn-group-sm">
                                        <form action="{{ route('admin.orders.approve', $order->id) }}" method="POST" class="d-inline approve-form">
                                            @csrf
                                            <button type="button" class="btn btn-outline-success btn-approve" title="Lunasi & Setujui">
                                                <i class="fas fa-check"></i>
                                            </button>
                                        </form>
                                        <button type="button" class="btn btn-outline-danger btn-cancel-order" data-id="{{ $order->id }}" title="Batalkan">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    </div>
                                @else
                                    -
                                @endif
                            </td>
                        </tr>
                        @empty
                        <tr>
                            <td colspan="8" class="text-center py-4 text-muted">Tidak ada data pesanan.</td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
            
            <div class="mt-3">
                {{ $orders->appends(['status' => $status, 'search' => $search])->links() }}
            </div>
        </div>
    </div>
</div>

<!-- Modal Batal Pesanan -->
<div class="modal fade" id="cancelModal" tabindex="-1" aria-labelledby="cancelModalLabel" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content border-0 shadow">
      <form id="cancelForm" method="POST">
          @csrf
          <div class="modal-header bg-danger text-white">
            <h5 class="modal-title" id="cancelModalLabel"><i class="fas fa-exclamation-triangle me-2"></i>Batalkan Pesanan</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <p>Apakah Anda yakin ingin membatalkan pesanan ini?</p>
            <div class="mb-3">
                <label class="form-label fw-bold">Alasan Pembatalan (Opsional)</label>
                <textarea name="reason" class="form-control" rows="3" placeholder="Contoh: Stok habis, atau biarkan kosong..."></textarea>
                <div class="form-text">Alasan ini akan terlihat oleh user (jika dikosongkan akan berisi tanda -).</div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Tutup</button>
            <button type="submit" class="btn btn-danger">Batalkan Pesanan</button>
          </div>
      </form>
    </div>
  </div>
</div>

@push('scripts')
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Approve Confirmation
        const approveButtons = document.querySelectorAll('.btn-approve');
        approveButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const form = this.closest('form');
                
                Swal.fire({
                    title: 'Setujui Pesanan?',
                    text: 'Pesanan akan dilunasi secara manual dan layanan (Saldo/VPN) akan langsung aktif!',
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonColor: '#198754',
                    cancelButtonColor: '#6c757d',
                    confirmButtonText: 'Ya, Setujui',
                    cancelButtonText: 'Batal'
                }).then((result) => {
                    if (result.isConfirmed) {
                        form.submit();
                    }
                });
            });
        });

        // Cancel Modal
        const cancelButtons = document.querySelectorAll('.btn-cancel-order');
        cancelButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                const form = document.getElementById('cancelForm');
                form.action = `/admin/orders/${id}/cancel`;
                
                const modal = new bootstrap.Modal(document.getElementById('cancelModal'));
                modal.show();
            });
        });
    });
</script>
@endpush
@endsection
