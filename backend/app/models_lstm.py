import torch
import torch.nn as nn


class EDArrivalsLSTM(nn.Module):
    """2-layer LSTM for hourly ED arrival forecasting."""

    def __init__(self, input_size: int = 1, hidden_size: int = 32, num_layers: int = 2, output_size: int = 1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1 if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 16),
            nn.ReLU(),
            nn.Linear(16, output_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch_size, seq_len, input_size)
        out, _ = self.lstm(x)
        # Take the output vector from the final time step
        last_step = out[:, -1, :]
        return self.fc(last_step)

