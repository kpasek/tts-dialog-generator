# coding:utf-8


from generators.stylish_model.stylish_lib.config_loader import ModelConfig


from .text_aligner import tdnn_blstm_ctc_model_base

from .discriminators.multi_period import MultiPeriodDiscriminator
from .discriminators.multi_resolution import MultiResolutionDiscriminator
from .discriminators.multi_subband import MultiScaleSubbandCQTDiscriminator

from .duration_predictor import DurationPredictor
from .pitch_energy_predictor import PitchEnergyPredictor

from .text_encoder import TextEncoder
from .fine_style_encoder import FineStyleEncoder
from .decoder import Decoder
from .ringformer import RingformerGenerator

from munch import Munch

import logging

logger = logging.getLogger(__name__)


def build_model(model_config: ModelConfig):
    text_aligner = tdnn_blstm_ctc_model_base(
        model_config.n_mels, model_config.text_encoder.tokens
    )
    assert model_config.generator.type in [
        "ringformer",
    ], "Decoder type unknown"

    if model_config.generator.type == "ringformer":
        decoder = Decoder(
            dim_in=model_config.inter_dim,
            style_dim=model_config.style_dim,
            dim_out=model_config.generator.upsample_initial_channel,
            hidden_dim=model_config.decoder.hidden_dim,
            residual_dim=model_config.decoder.residual_dim,
        )
        generator = RingformerGenerator(
            style_dim=model_config.style_dim,
            resblock_kernel_sizes=model_config.generator.resblock_kernel_sizes,
            upsample_rates=model_config.generator.upsample_rates,
            upsample_initial_channel=model_config.generator.upsample_initial_channel,
            resblock_dilation_sizes=model_config.generator.resblock_dilation_sizes,
            upsample_kernel_sizes=model_config.generator.upsample_kernel_sizes,
            gen_istft_n_fft=model_config.generator.gen_istft_n_fft,
            gen_istft_hop_size=model_config.generator.gen_istft_hop_size,
            sample_rate=model_config.sample_rate,
        )

    text_encoder = TextEncoder(
        inter_dim=model_config.inter_dim, config=model_config.text_encoder
    )
    text_duration_encoder = TextEncoder(
        inter_dim=model_config.inter_dim, config=model_config.text_encoder
    )

    textual_prosody_encoder = FineStyleEncoder(
        model_config.inter_dim,
        model_config.style_dim,
        model_config.style_encoder.layers,
    )
    textual_style_encoder = FineStyleEncoder(
        model_config.inter_dim,
        model_config.style_dim,
        model_config.style_encoder.layers,
    )

    duration_predictor = DurationPredictor(
        style_dim=model_config.style_dim,
        d_hid=model_config.inter_dim,
        nlayers=model_config.duration_predictor.n_layer,
        max_dur=model_config.duration_predictor.max_dur,
        dropout=model_config.duration_predictor.dropout,
    )

    pitch_energy_predictor = PitchEnergyPredictor(
        style_dim=model_config.style_dim,
        d_hid=model_config.inter_dim,
        dropout=model_config.pitch_energy_predictor.dropout,
    )
    nets = Munch(
        duration_predictor=duration_predictor,
        pitch_energy_predictor=pitch_energy_predictor,
        decoder=decoder,
        generator=generator,
        text_encoder=text_encoder,
        text_duration_encoder=text_duration_encoder,
        textual_prosody_encoder=textual_prosody_encoder,
        textual_style_encoder=textual_style_encoder,
        text_aligner=text_aligner,
        mpd=MultiPeriodDiscriminator(),
        msbd=MultiScaleSubbandCQTDiscriminator(sample_rate=model_config.sample_rate),
        mrd=MultiResolutionDiscriminator(),
    )

    return nets
