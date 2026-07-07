@extends('layouts.app')

@section('content')
<div class="container-fluid py-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h3 class="mb-1 text-dark fw-bold">Manajemen Bot Telegram</h3>
            <p class="text-secondary mb-0">Kelola user bot Telegram, approve permohonan akses, dan tambah kuota VPN.</p>
        </div>
    </div>

    <!-- Navigation Tabs -->
    <ul class="nav nav-pills nav-fill bg-white p-2 rounded shadow-sm mb-4 border" id="botTabs" role="tablist">
        <li class="nav-item" role="presentation">
            <button class="nav-link active fw-bold text-uppercase py-3 d-flex align-items-center justify-content-center gap-2" id="users-tab" data-bs-toggle="tab" data-bs-target="#users-pane" type="button" role="tab">
                <i class="fas fa-users-cog text-primary"></i> User Bot Telegram
                <span class="badge bg-primary rounded-pill">{{ $botUsers->count() }}</span>
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold text-uppercase py-3 d-flex align-items-center justify-content-center gap-2" id="access-tab" data-bs-toggle="tab" data-bs-target="#access-pane" type="button" role="tab">
                <i class="fas fa-key text-warning"></i> Permohonan Akses
                <span class="badge bg-warning text-dark rounded-pill">{{ $accessRequests->count() }}</span>
            </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link fw-bold text-uppercase py-3 d-flex align-items-center justify-content-center gap-2" id="quota-tab" data-bs-toggle="tab" data-bs-target="#quota-pane" type="button" role="tab">
                <i class="fas fa-chart-line text-success"></i> Permohonan Kuota
                <span class="badge bg-success rounded-pill">{{ $quotaRequests->count() }}</span>
            </button>
        </li>
    </ul>

    <div class="tab-content" id="botTabsContent">
        <!-- ─── TAB 1: USERS ────────────────────────────────────────────────── -->
        <div class="tab-pane fade show active" id="users-pane" role="tabpanel" tabindex="0">
            <div class="card shadow-sm border-0">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="bg-light">
                                <tr>
                                    <th class="px-4 py-3">Telegram User</th>
                                    <th class="px-4 py-3">Role</th>
                                    <th class="px-4 py-3">Status</th>
                                    <th class="px-4 py-3">SSH Limit</th>
                                    <th class="px-4 py-3">Xray Limit</th>
                                    <th class="px-4 py-3">Linked Web User</th>
                                    <th class="px-4 py-3 text-end">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                @forelse($botUsers as $bUser)
                                <tr class="account-row">
                                    <td data-label="Telegram User" class="px-4 py-3">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center text-white bg-info" style="width: 40px; height: 40px; font-weight: bold; text-transform: uppercase;">
                                                <i class="fab fa-telegram-plane"></i>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark">{{ $bUser->tg_full_name ?: 'No Name' }}</div>
                                                <div class="text-secondary small">{{ $bUser->tg_username ? '@' . $bUser->tg_username : 'No Username' }} (ID: {{ $bUser->tg_id }})</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td data-label="Role" class="px-4 py-3">
                                        <span class="badge @if($bUser->role === 'admin') bg-danger @elseif($bUser->role === 'reseller') bg-warning text-dark @else bg-primary @endif rounded-pill px-3">
                                            {{ ucfirst($bUser->role) }}
                                        </span>
                                    </td>
                                    <td data-label="Status" class="px-4 py-3">
                                        @if($bUser->status === 'approved')
                                            <span class="badge bg-success bg-opacity-10 text-success rounded-pill px-3 py-2 border border-success border-opacity-25"><i class="fas fa-check-circle me-1"></i> Approved</span>
                                        @elseif($bUser->status === 'pending')
                                            <span class="badge bg-warning bg-opacity-10 text-warning rounded-pill px-3 py-2 border border-warning border-opacity-25"><i class="fas fa-hourglass-half me-1"></i> Pending</span>
                                        @elseif($bUser->status === 'rejected')
                                            <span class="badge bg-secondary bg-opacity-10 text-secondary rounded-pill px-3 py-2 border border-secondary border-opacity-25"><i class="fas fa-times-circle me-1"></i> Rejected</span>
                                        @else
                                            <span class="badge bg-danger bg-opacity-10 text-danger rounded-pill px-3 py-2 border border-danger border-opacity-25"><i class="fas fa-ban me-1"></i> Suspended</span>
                                        @endif
                                    </td>
                                    <td data-label="SSH Limit" class="px-4 py-3 fw-bold">
                                        {{ $bUser->ssh_limit === 0 ? 'Unlimited' : $bUser->ssh_limit }}
                                    </td>
                                    <td data-label="Xray Limit" class="px-4 py-3 fw-bold">
                                        {{ $bUser->xray_limit === 0 ? 'Unlimited' : $bUser->xray_limit }}
                                    </td>
                                    <td data-label="Linked Web User" class="px-4 py-3">
                                        @if($bUser->webUser)
                                            <div class="fw-bold text-dark">{{ $bUser->webUser->name }}</div>
                                            <div class="text-secondary small">Saldo: Rp {{ number_format($bUser->webUser->balance, 0, ',', '.') }}</div>
                                        @else
                                            <span class="text-muted italic"><i class="fas fa-unlink text-danger me-1"></i> Belum terhubung</span>
                                        @endif
                                    </td>
                                    <td data-label="Aksi" class="px-4 py-3 text-md-end">
                                        <div class="d-flex justify-content-md-end gap-2">
                                            <button class="btn btn-sm btn-light text-primary" data-bs-toggle="modal" data-bs-target="#editBotUser{{ $bUser->id }}">
                                                <i class="fas fa-edit me-1"></i> Edit
                                            </button>
                                            <form action="{{ route('admin.bot.users.delete', $bUser->id) }}" method="POST" class="d-inline" onsubmit="return confirm('Apakah Anda yakin ingin menghapus user bot ini?');">
                                                @csrf
                                                @method('DELETE')
                                                <button type="submit" class="btn btn-sm btn-light text-danger">
                                                    <i class="fas fa-trash"></i>
                                                </button>
                                            </form>
                                        </div>
                                    </td>
                                </tr>

                                <!-- EDIT MODAL -->
                                <div class="modal fade" id="editBotUser{{ $bUser->id }}" tabindex="-1" aria-hidden="true">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <form action="{{ route('admin.bot.users.update', $bUser->id) }}" method="POST">
                                                @csrf
                                                <div class="modal-header">
                                                    <h5 class="modal-title">Edit User Bot Telegram</h5>
                                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                </div>
                                                <div class="modal-body text-start">
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Telegram ID</label>
                                                        <input type="text" class="form-control border bg-light" value="{{ $bUser->tg_id }}" readonly>
                                                    </div>
                                                    <div class="row mb-3">
                                                        <div class="col-6">
                                                            <label class="form-label fw-bold">Role</label>
                                                            <select class="form-select border" name="role">
                                                                <option value="user" {{ $bUser->role === 'user' ? 'selected' : '' }}>User</option>
                                                                <option value="reseller" {{ $bUser->role === 'reseller' ? 'selected' : '' }}>Reseller</option>
                                                                <option value="admin" {{ $bUser->role === 'admin' ? 'selected' : '' }}>Admin</option>
                                                            </select>
                                                        </div>
                                                        <div class="col-6">
                                                            <label class="form-label fw-bold">Status</label>
                                                            <select class="form-select border" name="status">
                                                                <option value="approved" {{ $bUser->status === 'approved' ? 'selected' : '' }}>Approved</option>
                                                                <option value="pending" {{ $bUser->status === 'pending' ? 'selected' : '' }}>Pending</option>
                                                                <option value="rejected" {{ $bUser->status === 'rejected' ? 'selected' : '' }}>Rejected</option>
                                                                <option value="suspended" {{ $bUser->status === 'suspended' ? 'selected' : '' }}>Suspended</option>
                                                            </select>
                                                        </div>
                                                    </div>
                                                    <div class="row mb-3">
                                                        <div class="col-6">
                                                            <label class="form-label fw-bold">Limit Pembuatan SSH</label>
                                                            <input type="number" class="form-control border" name="ssh_limit" value="{{ $bUser->ssh_limit }}" min="0" required>
                                                            <small class="text-muted">Isi 0 untuk tanpa batas.</small>
                                                        </div>
                                                        <div class="col-6">
                                                            <label class="form-label fw-bold">Limit Pembuatan Xray</label>
                                                            <input type="number" class="form-control border" name="xray_limit" value="{{ $bUser->xray_limit }}" min="0" required>
                                                            <small class="text-muted">Isi 0 untuk tanpa batas.</small>
                                                        </div>
                                                    </div>
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Hubungkan dengan User Web</label>
                                                        <select class="form-select border" name="user_id">
                                                            <option value="">-- Jangan Hubungkan (Tanpa Saldo) --</option>
                                                            @foreach($webUsers as $wUser)
                                                                <option value="{{ $wUser->id }}" {{ $bUser->user_id == $wUser->id ? 'selected' : '' }}>{{ $wUser->name }} ({{ $wUser->username ?? $wUser->email }}) - Saldo: Rp {{ number_format($wUser->balance, 0, ',', '.') }}</option>
                                                            @endforeach
                                                        </select>
                                                        <small class="text-muted">Penting untuk sinkronisasi saldo saat customer melakukan topup/pembelian di bot.</small>
                                                    </div>
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Catatan Admin</label>
                                                        <input type="text" class="form-control border" name="note" value="{{ $bUser->note }}">
                                                    </div>
                                                </div>
                                                <div class="modal-footer">
                                                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                                    <button type="submit" class="btn btn-primary">Simpan</button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                                @empty
                                <tr>
                                    <td colspan="7" class="text-center py-5">
                                        <div class="text-muted"><i class="fas fa-users-slash fs-1 mb-3"></i></div>
                                        <div class="text-muted fw-bold">Tidak ada user bot Telegram terdaftar.</div>
                                    </td>
                                </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- ─── TAB 2: ACCESS REQUESTS ───────────────────────────────────────── -->
        <div class="tab-pane fade" id="access-pane" role="tabpanel" tabindex="0">
            <div class="card shadow-sm border-0">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="bg-light">
                                <tr>
                                    <th class="px-4 py-3">Telegram User</th>
                                    <th class="px-4 py-3">Alasan / Pesan</th>
                                    <th class="px-4 py-3">Tanggal Permohonan</th>
                                    <th class="px-4 py-3 text-end">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                @forelse($accessRequests as $req)
                                <tr class="account-row">
                                    <td class="px-4 py-3">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center text-white bg-warning" style="width: 40px; height: 40px; font-weight: bold;">
                                                <i class="fas fa-user-plus text-dark"></i>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark">{{ $req->tg_full_name ?: 'No Name' }}</div>
                                                <div class="text-secondary small">{{ $req->tg_username ? '@' . $req->tg_username : 'No Username' }} (ID: {{ $req->tg_id }})</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td class="px-4 py-3">
                                        <span class="text-dark">{{ $req->reason ?: '-' }}</span>
                                    </td>
                                    <td class="px-4 py-3">
                                        <span class="text-secondary small">{{ $req->created_at ? $req->created_at->format('d M Y H:i:s') : '-' }}</span>
                                    </td>
                                    <td class="px-4 py-3 text-end">
                                        <div class="d-flex justify-content-end gap-2">
                                            <button class="btn btn-sm btn-success" data-bs-toggle="modal" data-bs-target="#approveAccess{{ $req->id }}">
                                                <i class="fas fa-check me-1"></i> Approve
                                            </button>
                                            <button class="btn btn-sm btn-danger" data-bs-toggle="modal" data-bs-target="#rejectAccess{{ $req->id }}">
                                                <i class="fas fa-times me-1"></i> Reject
                                            </button>
                                        </div>
                                    </td>
                                </tr>

                                <!-- APPROVE MODAL -->
                                <div class="modal fade" id="approveAccess{{ $req->id }}" tabindex="-1" aria-hidden="true">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <form action="{{ route('admin.bot.access.approve', $req->id) }}" method="POST">
                                                @csrf
                                                <div class="modal-header">
                                                    <h5 class="modal-title">Setujui Request Akses</h5>
                                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                </div>
                                                <div class="modal-body text-start">
                                                    <p>Apakah Anda yakin ingin menyetujui akses Telegram untuk <strong>{{ $req->tg_full_name }}</strong> (ID: {{ $req->tg_id }})?</p>
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Catatan Persetujuan (Opsional)</label>
                                                        <input type="text" class="form-control border" name="reason" placeholder="Contoh: Disetujui oleh admin">
                                                    </div>
                                                </div>
                                                <div class="modal-footer">
                                                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                                    <button type="submit" class="btn btn-success">Setujui</button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                </div>

                                <!-- REJECT MODAL -->
                                <div class="modal fade" id="rejectAccess{{ $req->id }}" tabindex="-1" aria-hidden="true">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <form action="{{ route('admin.bot.access.reject', $req->id) }}" method="POST">
                                                @csrf
                                                <div class="modal-header">
                                                    <h5 class="modal-title text-danger">Tolak Request Akses</h5>
                                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                </div>
                                                <div class="modal-body text-start">
                                                    <p>Apakah Anda yakin ingin menolak akses Telegram untuk <strong>{{ $req->tg_full_name }}</strong> (ID: {{ $req->tg_id }})?</p>
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Alasan Penolakan</label>
                                                        <input type="text" class="form-control border" name="reason" placeholder="Contoh: Identitas tidak dikenal" required>
                                                    </div>
                                                </div>
                                                <div class="modal-footer">
                                                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                                    <button type="submit" class="btn btn-danger">Tolak Request</button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                                @empty
                                <tr>
                                    <td colspan="4" class="text-center py-5">
                                        <div class="text-muted"><i class="fas fa-check-double fs-1 mb-3 text-success"></i></div>
                                        <div class="text-muted fw-bold">Tidak ada permohonan akses tertunda.</div>
                                    </td>
                                </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- ─── TAB 3: QUOTA REQUESTS ────────────────────────────────────────── -->
        <div class="tab-pane fade" id="quota-pane" role="tabpanel" tabindex="0">
            <div class="card shadow-sm border-0">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="bg-light">
                                <tr>
                                    <th class="px-4 py-3">Telegram User</th>
                                    <th class="px-4 py-3">Alasan Tambah Kuota</th>
                                    <th class="px-4 py-3">Tanggal Permohonan</th>
                                    <th class="px-4 py-3 text-end">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                @forelse($quotaRequests as $qReq)
                                @php
                                    $btUser = \App\Models\TelegramBotUser::where('tg_id', $qReq->tg_id)->first();
                                @endphp
                                <tr class="account-row">
                                    <td class="px-4 py-3">
                                        <div class="d-flex align-items-center gap-3">
                                            <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center text-white bg-success" style="width: 40px; height: 40px; font-weight: bold;">
                                                <i class="fas fa-chart-bar"></i>
                                            </div>
                                            <div>
                                                <div class="fw-bold text-dark">{{ $btUser ? $btUser->tg_full_name : 'Telegram User' }}</div>
                                                <div class="text-secondary small">ID: {{ $qReq->tg_id }}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td class="px-4 py-3">
                                        <span class="text-dark">{{ $qReq->reason ?: '-' }}</span>
                                    </td>
                                    <td class="px-4 py-3">
                                        <span class="text-secondary small">{{ $qReq->created_at ? $qReq->created_at->format('d M Y H:i:s') : '-' }}</span>
                                    </td>
                                    <td class="px-4 py-3 text-end">
                                        <div class="d-flex justify-content-end gap-2">
                                            <button class="btn btn-sm btn-success" data-bs-toggle="modal" data-bs-target="#approveQuota{{ $qReq->id }}">
                                                <i class="fas fa-plus me-1"></i> Approve & Tambah
                                            </button>
                                            <button class="btn btn-sm btn-danger" data-bs-toggle="modal" data-bs-target="#rejectQuota{{ $qReq->id }}">
                                                <i class="fas fa-times me-1"></i> Reject
                                            </button>
                                        </div>
                                    </td>
                                </tr>

                                <!-- APPROVE QUOTA MODAL -->
                                <div class="modal fade" id="approveQuota{{ $qReq->id }}" tabindex="-1" aria-hidden="true">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <form action="{{ route('admin.bot.quota.approve', $qReq->id) }}" method="POST">
                                                @csrf
                                                <div class="modal-header">
                                                    <h5 class="modal-title">Setujui & Tambah Kuota VPN</h5>
                                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                </div>
                                                <div class="modal-body text-start">
                                                    <p>Pilih jumlah kuota tambahan yang ingin diberikan kepada user (ID: {{ $qReq->tg_id }}):</p>
                                                    <div class="row mb-3">
                                                        <div class="col-6">
                                                            <label class="form-label fw-bold">Tambah Kuota SSH</label>
                                                            <input type="number" class="form-control border" name="ssh_add" value="1" min="0" required>
                                                        </div>
                                                        <div class="col-6">
                                                            <label class="form-label fw-bold">Tambah Kuota Xray</label>
                                                            <input type="number" class="form-control border" name="xray_add" value="2" min="0" required>
                                                        </div>
                                                    </div>
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Catatan Admin (Opsional)</label>
                                                        <input type="text" class="form-control border" name="reason" placeholder="Contoh: Bonus limit awal">
                                                    </div>
                                                </div>
                                                <div class="modal-footer">
                                                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                                    <button type="submit" class="btn btn-success">Approve & Tambah</button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                </div>

                                <!-- REJECT QUOTA MODAL -->
                                <div class="modal fade" id="rejectQuota{{ $qReq->id }}" tabindex="-1" aria-hidden="true">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <form action="{{ route('admin.bot.quota.reject', $qReq->id) }}" method="POST">
                                                @csrf
                                                <div class="modal-header">
                                                    <h5 class="modal-title text-danger">Tolak Request Tambah Kuota</h5>
                                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                </div>
                                                <div class="modal-body text-start">
                                                    <p>Apakah Anda yakin ingin menolak permohonan tambah kuota dari user (ID: {{ $qReq->tg_id }})?</p>
                                                    <div class="mb-3">
                                                        <label class="form-label fw-bold">Alasan Penolakan</label>
                                                        <input type="text" class="form-control border" name="reason" placeholder="Contoh: Kuota masih mencukupi" required>
                                                    </div>
                                                </div>
                                                <div class="modal-footer">
                                                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                                                    <button type="submit" class="btn btn-danger">Tolak Request</button>
                                                </div>
                                            </form>
                                        </div>
                                    </div>
                                </div>
                                @empty
                                <tr>
                                    <td colspan="4" class="text-center py-5">
                                        <div class="text-muted"><i class="fas fa-check-double fs-1 mb-3 text-success"></i></div>
                                        <div class="text-muted fw-bold">Tidak ada permohonan kuota tertunda.</div>
                                    </td>
                                </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection
