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
                            <th class="px-4 py-3">Saldo</th>
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
                            <td data-label="Limit Akun VPN" class="px-4 py-3">
                                <div class="fw-bold">{{ $user->vpn_account_limit }}</div>
                                <div class="small text-secondary">Akun Aktif</div>
                            </td>
                            <td data-label="Saldo" class="px-4 py-3">
                                <div class="fw-bold text-success">Rp {{ number_format($user->balance, 0, ',', '.') }}</div>
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
                                    @if($user->id !== auth()->id())
                                    <div class="dropdown">
                                        <button class="btn btn-sm btn-light text-primary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                            <i class="fas fa-cog"></i> Aksi
                                        </button>
                                        <ul class="dropdown-menu dropdown-menu-end shadow border-0">
                                            <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#editUser{{ $user->id }}"><i class="fas fa-edit me-2 text-primary"></i>Edit Profile</a></li>
                                            <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#resetPassword{{ $user->id }}"><i class="fas fa-key me-2 text-warning"></i>Reset Password</a></li>
                                            <li><a class="dropdown-item" href="#" data-bs-toggle="modal" data-bs-target="#injectBalance{{ $user->id }}"><i class="fas fa-wallet me-2 text-success"></i>Inject Saldo</a></li>
                                            @if($user->telegram_id)
                                            <li>
                                                <form action="{{ route('admin.users.unlink-telegram', $user->id) }}" method="POST" class="d-inline" onsubmit="return confirm('Lepas tautan Telegram untuk user ini?');">
                                                    @csrf
                                                    <button type="submit" class="dropdown-item"><i class="fas fa-unlink me-2 text-danger"></i>Unlink Telegram</button>
                                                </form>
                                            </li>
                                            @endif
                                            <li><hr class="dropdown-divider"></li>
                                            <li>
                                                <form action="{{ route('admin.users.delete', $user->id) }}" method="POST" class="d-inline" onsubmit="return confirm('Apakah Anda yakin ingin menghapus akun user ini secara permanen?');">
                                                    @csrf
                                                    @method('DELETE')
                                                    <button type="submit" class="dropdown-item text-danger"><i class="fas fa-trash me-2"></i>Hapus User</button>
                                                </form>
                                            </li>
                                        </ul>
                                    </div>
                                    @else
                                    <span class="badge bg-secondary">Self</span>
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

                        <!-- Modal Reset Password -->
                        <div class="modal fade" id="resetPassword{{ $user->id }}" tabindex="-1" aria-hidden="true">
                            <div class="modal-dialog modal-dialog-centered">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">Reset Password: {{ $user->username ?? $user->name }}</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                    </div>
                                    <form action="{{ route('admin.users.reset-password', $user->id) }}" method="POST">
                                        @csrf
                                        <div class="modal-body">
                                            <div class="mb-3">
                                                <label class="form-label fw-bold">Password Baru</label>
                                                <input type="password" name="new_password" class="form-control" required minlength="6" placeholder="Masukkan password baru">
                                                <div class="form-text">Password harus terdiri dari minimal 6 karakter.</div>
                                            </div>
                                        </div>
                                        <div class="modal-footer">
                                            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                            <button type="submit" class="btn btn-warning">Reset Password</button>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>

                        <!-- Modal Inject Saldo -->
                        <div class="modal fade" id="injectBalance{{ $user->id }}" tabindex="-1">
                            <div class="modal-dialog modal-dialog-centered">
                                <div class="modal-content border-0 shadow-lg">
                                    <div class="modal-header bg-success text-white">
                                        <h5 class="modal-title"><i class="fas fa-wallet me-2"></i>Kelola Saldo {{ $user->name }}</h5>
                                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body p-4">
                                        <div class="alert alert-info mb-4">
                                            <div class="fw-bold">Saldo Saat Ini:</div>
                                            <div class="fs-4">Rp {{ number_format($user->balance, 0, ',', '.') }}</div>
                                        </div>
                                        
                                        <form action="{{ route('admin.users.inject-balance', $user->id) }}" method="POST" class="mb-4">
                                            @csrf
                                            <div class="mb-3">
                                                <label class="form-label fw-bold">Tambah Saldo</label>
                                                <div class="input-group">
                                                    <span class="input-group-text">Rp</span>
                                                    <input type="number" name="amount" class="form-control" required min="1" placeholder="Contoh: 50000">
                                                </div>
                                            </div>
                                            <button type="submit" class="btn btn-success w-100">Inject Saldo</button>
                                        </form>

                                        <hr>

                                        <form action="{{ route('admin.users.block-balance', $user->id) }}" method="POST" onsubmit="return confirm('Anda yakin ingin me-nol-kan saldo user ini?');">
                                            @csrf
                                            <button type="submit" class="btn btn-outline-danger w-100"><i class="fas fa-ban me-2"></i>Blokir / Hapus Saldo Jadi 0</button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
                        @empty
                        <tr>
                            <td colspan="7" class="text-center py-4 text-muted">
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
