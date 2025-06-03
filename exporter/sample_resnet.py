import torch
import torch.nn as nn
import numpy as np
import torchvision.datasets as dataset
import torchvision.transforms as transform
from torch.utils.data import DataLoader
import time

# 데이터셋 정의
cifar10_train = None
cifar10_test = None

# 모델 정의
class ResNet(nn.Module):
    def __init__(self):
        super(ResNet, self).__init__()

        self.conv1_1 = nn.Conv2d(3, 16, kernel_size=3, padding=1)
        self.conv1_2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)

        self.conv2_1 = nn.Conv2d(32, 32, kernel_size=3, padding=1)
        self.conv2_2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)

        self.conv3_1 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv3_2 = nn.Conv2d(128, 256, kernel_size=3, padding=1)

        self.conv1_skip = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2_skip = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3_skip = nn.Conv2d(64, 256, kernel_size=3, padding=1)

        self.fc1 = nn.Linear(4096, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, 10)

        self.relu = nn.ReLU()
        self.avgPool2d = nn.AvgPool2d(kernel_size=2, stride=2)

    def forward(self, x):
        input_feature1 = x
        out = self.relu(self.conv1_1(x))
        out = self.relu(self.conv1_2(out))
        input_skip1 = self.relu(self.conv1_skip(input_feature1))
        out = torch.add(out, input_skip1)
        out = self.avgPool2d(out)

        input_feature2 = out
        out = self.relu(self.conv2_1(out))
        out = self.relu(self.conv2_2(out))
        input_skip2 = self.relu(self.conv2_skip(input_feature2))
        out = torch.add(out, input_skip2)
        out = self.avgPool2d(out)

        input_feature3 = out
        out = self.relu(self.conv3_1(out))
        out = self.relu(self.conv3_2(out))
        input_skip3 = self.relu(self.conv3_skip(input_feature3))
        out = torch.add(out, input_skip3)
        out = self.avgPool2d(out)

        out = out.reshape(-1, 4096)
        out = self.relu(self.fc1(out))
        out = self.relu(self.fc2(out))
        out = self.fc3(out)

        return out

# 하이퍼파라미터 및 구성 객체 (외부 참조 가능)
batch_size = 100
learning_rate = 0.1
training_epochs = 20
loss_function = nn.CrossEntropyLoss()
network = ResNet()
optimizer = torch.optim.SGD(network.parameters(), lr=learning_rate)

device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

# 학습 및 평가 블록
if __name__ == "__main__":
    cifar10_train = dataset.CIFAR10(root="./", train=True, transform=transform.ToTensor(), download=True)
    cifar10_test = dataset.CIFAR10(root="./", train=False, transform=transform.ToTensor(), download=True)
    data_loader = DataLoader(dataset=cifar10_train, batch_size=batch_size, shuffle=True, drop_last=True)

    network = network.to(device)

    for epoch in range(training_epochs):
        start_time = time.time()
        avg_cost = 0
        total_batch = len(data_loader)

        for img, label in data_loader:
            img = img.to(device)
            label = label.to(device)

            pred = network(img)
            loss = loss_function(pred, label)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            avg_cost += loss / total_batch

        end_time = time.time()
        epoch_time = end_time - start_time
        print(f'Epoch: {epoch+1:2d} | Loss = {avg_cost:.4f} | Time = {epoch_time:.2f} sec')

    print('Learning finished!')

    # 정확도 평가
    network = network.to('cpu')
    with torch.no_grad():
        img_test = torch.tensor(np.transpose(cifar10_test.data, (0, 3, 1, 2))) / 255.
        label_test = torch.tensor(cifar10_test.targets)

        prediction = network(img_test)
        correct_prediction = torch.argmax(prediction, 1) == label_test
        accuracy = correct_prediction.float().mean()
        print('Accuracy:', accuracy.item())
