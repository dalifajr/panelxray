@extends('layouts.app')

@section('content')
<div class="container-fluid py-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h3 class="mb-1 text-dark fw-bold">Manajemen User</h3>
            <p class="text-secondary mb-0">Kelola pengguna web panel, hak akses, dan batas pembuatan akun VPN.</p>
        </div>
    </div>

    <div class="card shadow-sm border-0 mb-4">
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead class="bg-light">
                        <tr>
                            <th class="px-4 py-3">User</th>
                            <th class="px-4 py-3">Role</th>
                            <th class="px-4 py-3">Limit Akun VPN</th>
                            <th class="px-4 py-3">Akun Dibuat</th>
                            <th class="px-4 py-3 text-center">Status</th>
                            <th class="px-4 py-3 text-end">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse($users as $user)
                        <tr class="account-row">
                            <td data-label="User" class="px-4 py-3">
                                <div class="d-flex align-items-center gap-3">
                                    <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center text-white {{ $user->role === 'admin' ? 'bg-danger' : 'bg-primary' }}" style="width: 40px; height: 40px; font-weight: bold; text-transform: uppercase;">
                                        {{ substr($user->name, 0, 1) }}
                                    </div>
                                    <div>
                                        <div class="fw-bold text-dark">{{ $user->name }}</div>
                                        <div class="text-secondary small">{{ $user->username ?? $user->email }}</div>
                                        @if($user->telegram_id)
                                        <div class="text-info small"><i class="fab fa-telegram"></i> {{ $user->telegram_id }}</div>
                                        @endif
                                    </div>
                                </div>
                            </td>
                            <td data-label="Role" class="px-4 py-3">
                                <span class="badge {{ $user->role === 'admin' ? 'bg-danger' : 'bg-primary' }} rounded-pill px-3">
                                    {{ ucfirst($user->role) }}
                                </span>
                            </td>
                            <td data-label="Limit VPN" class="px-4 py-3">
                                <span class="fw-bold">{{ $user->vpn_account_limit }}</span> akun aktif
                            </td>
                            <td data-label="Akun Dibuat" class="px-4 py-3">
                                <span class="fw-bold">{{ $user->vpn_accounts_count }}</span>
                            </td>
                            <td data-label="Status" class="px-4 py-3 text-md-center">
                                @if($user->status === 'active')
                                    <span class="badge bg-success bg-opacity-10 text-success rounded-pill px-3 py-2 border border-success border-opacity-25"><i class="fas fa-check-circle me-1"></i> Active</span>
                                @else
                                    <span class="badge bg-danger bg-opacity-10 text-danger rounded-pill px-3 py-2 border border-danger border-opacity-25"><i class="fas fa-ban me-1"></i> Suspended</span>
                                @endif
                            </td>
                            <td data-label="Aksi" class="px-4 py-3 text-md-end">
                                <div class="d-flex justify-content-md-end gap-2">
                                    <button class="btn btn-sm btn-light text-primary" data-bs-toggle="modal" data-bs-target="#editUser{{ $user->id }}" title="Edit User">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    @if($user->id !== auth()->id())
                                    <form action="{{ route('admin.users.delete', $user->id) }}" method="POST" class="d-inline" onsubmit="return confirm('Apakah Anda yakin ingin menghapus user ini secara permanen?');">
                                        @csrf
                                        @method('DELETE')
                                        <button type="submit" class="btn btn-sm btn-light text-danger" title="Hapus User">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </form>
                                    @endif
                                </div>
                            </td>
                        </tr>

                        <!-- Modal Edit User -->
                        <div class="modal fade" id="editUser{{ $user->id }}" tabindex="-1" aria-hidden="true">
                            <div class="modal-dialog modal-dialog-centered">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">Edit User: {{ $user->username ?? $user->name }}</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                    </div>
                                    <form action="{{ route('admin.users.update', $user->id) }}" method="POST">
                                        @csrf
                                        <div class="modal-body">
                                            <div class="mb-3">
                                                <label class="form-label fw-bold">Role</label>
                                                <select name="role" class="form-select">
                                                    <option value="customer" {{ $user->role === 'customer' ? 'selected' : '' }}>Customer</option>
                                                    <option value="admin" {{ $user->role === 'admin' ? 'selected' : '' }}>Admin</option>
                                                </select>
                                                <div class="form-text text-warning"><i class="fas fa-exclamation-triangle"></i> Admin memiliki kontrol penuh atas panel ini.</div>
                                            </div>
                                            
                                            <div class="mb-3">
                                                <label class="form-label fw-bold">Limit Akun VPN</label>
                                                <input type="number" name="vpn_account_limit" class="form-control" value="{{ $user->vpn_account_limit }}" min="0" required>
                                                <div class="form-text">Batas jumlah akun VPN aktif yang dapat dibuat oleh user ini.</div>
                                            </div>

                                            <div class="mb-3">
                                                <label class="form-label fw-bold">Status Akun</label>
                                                <select name="status" class="form-select">
                                                    <option value="active" {{ $user->status === 'active' ? 'selected' : '' }}>Active</option>
                                                    <option value="suspended" {{ $user->status === 'suspended' ? 'selected' : '' }}>Suspended</option>
                                                </select>
                                                <div class="form-text">Jika "Suspended", user tidak akan bisa login ke web panel.</div>
                                            </div>
                                        </div>
                                        <div class="modal-footer">
                                            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                            <button type="submit" class="btn btn-primary">Simpan Perubahan</button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                        @empty
                        <tr>
                            <td colspan="6" class="text-center py-4 text-muted">
                                <i class="fas fa-folder-open fs-1 text-light mb-3 d-block"></i>
                                Belum ada user terdaftar
                            </td>
                        </tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
@endsection
