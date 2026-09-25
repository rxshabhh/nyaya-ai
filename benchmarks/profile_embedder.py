"""Compile and profile the sentence embedder on a real Snapdragon X Elite via Qualcomm AI Hub."""
import torch
import qai_hub as hub
from transformers import AutoModel

NAME = "sentence-transformers/all-MiniLM-L6-v2"
SEQ = 128                              # the NPU needs a fixed input length
DEVICE = "Snapdragon X Elite CRD"      


class Embedder(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.model = AutoModel.from_pretrained(NAME)

    def forward(self, input_ids, attention_mask):
        out = self.model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        mask = attention_mask.unsqueeze(-1).float()
        return (out * mask).sum(1) / mask.sum(1)   # mean pooling = one vector per paragraph


example = (torch.ones(1, SEQ, dtype=torch.int32), torch.ones(1, SEQ, dtype=torch.int32))
traced = torch.jit.trace(Embedder().eval(), example)

device = hub.Device(DEVICE)
compile_job = hub.submit_compile_job(
    model=traced,
    device=device,
    input_specs={"input_ids": ((1, SEQ), "int32"), "attention_mask": ((1, SEQ), "int32")},
    options="--target_runtime precompiled_qnn_onnx",
)
profile_job = hub.submit_profile_job(model=compile_job.get_target_model(), device=device)
print("Profile results:", profile_job.url)
