"""
Text Aligner


"""

import math
from typing import List, Tuple
import torch
from torch import nn
from torch.nn import TransformerEncoder
import torch.nn.functional as F
from einops import rearrange


def tdnn_blstm_ctc_model(
    input_dim: int, num_symbols: int, hidden_dim=640, drop_out=0.1, tdnn_blstm_spec=[]
):
    r"""Builds TDNN-BLSTM-based CTC tts_model."""
    encoder = TdnnBlstm(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        drop_out=drop_out,
        tdnn_blstm_spec=tdnn_blstm_spec,
    )
    encoder_output_layer = nn.Linear(hidden_dim, num_symbols + 1)

    return CTCModel(
        encoder, encoder_output_layer, n_token=num_symbols, n_mels=input_dim
    )


def tdnn_blstm_ctc_model_base(n_mels, num_symbols):
    return tdnn_blstm_ctc_model(
        input_dim=n_mels,
        num_symbols=num_symbols,
        hidden_dim=640,
        drop_out=0.1,
        tdnn_blstm_spec=[
            ("tdnn", 5, 2, 1),
            ("tdnn", 3, 1, 1),
            ("tdnn", 3, 1, 1),
            ("ffn", 5),
        ],
    )


class CTCModel(torch.nn.Module):
    r"""
    This implements a CTC tts_model with an encoder and a projection layer
    """

    def __init__(self, encoder, encoder_output_layer, n_token, n_mels) -> None:
        super().__init__()
        self.encoder = encoder
        self.encoder_output_layer = encoder_output_layer

    def ctc_output(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
          x:
            The output tensor from the transformer encoder.
            Its shape is (B, T', D')

        Returns:
          Return a tensor that can be used for CTC decoding.
          Its shape is (B, T, V), where V is the number of classes
        """
        x = x.permute(1, 0, 2)  # (N, T, C) -> (T, N, C)
        x = nn.functional.log_softmax(x, dim=-1)  # (T, N, C)
        return x

    def forward(
        self,
        sources: torch.Tensor,
        source_lengths: torch.Tensor,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, List[List[torch.Tensor]]]:
        r"""Forward pass for training.

        B: batch size;
        T: maximum source sequence length in batch;
        U: maximum target sequence length in batch;
        D: feature dimension of each source sequence element.

        Args:
            sources (torch.Tensor): source frame sequences right-padded with right context, with
                shape `(B, T, D)`.
            source_lengths (torch.Tensor): with shape `(B,)` and i-th element representing
                number of valid frames for i-th batch element in ``sources``.
            targets (torch.Tensor): target sequences, with shape `(B, U)` and each element
                mapping to a target symbol.
            target_lengths (torch.Tensor): with shape `(B,)` and i-th element representing
                number of valid frames for i-th batch element in ``targets``.
            predictor_state (List[List[torch.Tensor]] or None, optional): list of lists of tensors
                representing prediction network internal state generated in preceding invocation
                of ``forward``. (Default: ``None``)

        Returns:
            (torch.Tensor, torch.Tensor, torch.Tensor, List[List[torch.Tensor]]):
                torch.Tensor
                    joint network output, with shape
                    `(B, max output source length, max output target length, output_dim (number of target symbols))`.
                torch.Tensor
                    output source lengths, with shape `(B,)` and i-th element representing
                    number of valid elements along dim 1 for i-th batch element in joint network output.
                torch.Tensor
                    output target lengths, with shape `(B,)` and i-th element representing
                    number of valid elements along dim 2 for i-th batch element in joint network output.
                List[List[torch.Tensor]]
                    output states; list of lists of tensors
                    representing prediction network internal state generated in current invocation
                    of ``forward``.
        """
        device = self.encoder_output_layer.weight.device
        if sources.device != device:
            sources = sources.to(device)
            source_lengths = source_lengths.to(device)

        source_encodings, source_lengths = self.encoder(
            input=sources,
            lengths=source_lengths,
        )

        posterior = self.encoder_output_layer(source_encodings)
        ctc_log_prob = self.ctc_output(posterior)

        return ctc_log_prob, None  # mels


class TdnnBlstm(nn.Module):
    def __init__(
        self,
        input_dim: int,
        hidden_dim=640,
        drop_out=0.1,
        tdnn_blstm_spec=[],
    ) -> None:
        """
        Args:

          tdnn_blstm_spec:
            It is a list of network specifications. It can be either:
            - ('tdnn', kernel_size, stride, dilation)
            - ('blstm')
        """
        super().__init__()

        self.tdnn_blstm_spec = tdnn_blstm_spec

        layers = nn.ModuleList([])
        layers_info = []
        for i_layer, spec in enumerate(tdnn_blstm_spec):
            if spec[0] == "tdnn":
                ll = []
                dilation = spec[3] if len(spec) >= 4 else 1
                padding = int((spec[1] - 1) / 2) * dilation
                ll.append(
                    nn.Conv1d(
                        in_channels=input_dim if len(layers) == 0 else hidden_dim,
                        out_channels=hidden_dim,
                        kernel_size=spec[1],  # 3
                        dilation=dilation,
                        stride=spec[2],  # 1
                        padding=padding,  # 1
                    )
                )
                ll.append(nn.ReLU(inplace=True))
                ll.append(nn.BatchNorm1d(num_features=hidden_dim, affine=False))
                if drop_out > 0:
                    ll.append(nn.Dropout(drop_out))

                # The last dimension indicates the stride size
                # If stride > 1, then we need to recompute the lengths of input after this layer
                layers.append(nn.Sequential(*ll))
                layers_info.append(("tdnn", spec))

            elif spec[0] == "blstm":
                layers.append(
                    Blstm_with_skip(
                        input_dim=input_dim if len(layers) == 0 else hidden_dim,
                        hidden_dim=hidden_dim,
                        out_dim=hidden_dim,
                        skip=(
                            False
                            if len(layers) == 0 and input_dim != hidden_dim
                            else True
                        ),
                        drop_out=drop_out,
                    )
                )
                layers_info.append(("blstm", None))

            elif spec[0] == "ffn":
                layers.append(
                    Ffn(
                        input_dim=input_dim if len(layers) == 0 else hidden_dim,
                        hidden_dim=hidden_dim,
                        out_dim=hidden_dim,
                        skip=True,
                        drop_out=drop_out,
                        nlayers=spec[1],
                    )
                )
                layers_info.append(("ffn", spec))

        self.layers = layers
        self.layers_info = layers_info

    def forward(self, input: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        """
        Args:
          x:
            Its shape is [N, T, C]

        Returns:
          The output tensor has shape [N, T, C]
        """
        x = input
        for layer, (layer_type, spec) in zip(self.layers, self.layers_info):
            if layer_type == "tdnn":
                mask = (
                    torch.arange(lengths.max(), device=x.device)[None, :]
                    < lengths[:, None]
                ).float()
                x = x * mask.unsqueeze(2)  # masking/padding
                x = x.permute(0, 2, 1)  # (N, T, C) ->(N, C, T)
                x = layer(x)
                x = x.permute(0, 2, 1)  # (N, C, T) ->(N, T, C)

                stride = spec[2]
                if True:  # stride > 1:
                    kernel_size = spec[1]
                    dilation = spec[3] if len(spec) >= 4 else 1
                    padding = int((spec[1] - 1) / 2) * dilation
                    lengths = lengths + 2 * padding - dilation * (kernel_size - 1) - 1
                    lengths = lengths / stride + 1
                    lengths = torch.floor(lengths)
            elif layer_type == "blstm":
                x = layer(x, lengths)
            else:
                x = layer(x)
        return x, lengths


class Ffn(nn.Module):
    def __init__(
        self, input_dim, hidden_dim, out_dim, nlayers=1, drop_out=0.1, skip=False
    ) -> None:
        super().__init__()

        layers = []
        for ilayer in range(nlayers):
            _in = hidden_dim if ilayer > 0 else input_dim
            _out = hidden_dim if ilayer < nlayers - 1 else out_dim
            layers.extend(
                [
                    nn.Linear(_in, _out),
                    nn.ReLU(),
                    nn.Dropout(p=drop_out),
                ]
            )
        self.ffn = torch.nn.Sequential(
            *layers,
        )

        self.skip = skip

    def forward(self, x) -> torch.Tensor:
        x_out = self.ffn(x)

        if self.skip:
            x_out = x_out + x

        return x_out
