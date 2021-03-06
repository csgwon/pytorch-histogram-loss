import torch

from numpy.testing import assert_almost_equal
from torch.autograd import Variable

class HistogramLoss(torch.nn.Module):
    def __init__(self, num_steps, cuda=True):
        super(HistogramLoss, self).__init__()
        self.step = 2 / (num_steps - 1)
        self.cuda = cuda
        self.t = torch.arange(-1, 1+self.step, self.step).view(-1, 1)
        self.tsize = self.t.size()[0]
        if self.cuda:
            self.t = self.t.cuda()
        
    def forward(self, features, classes):
        def histogram(inds, size):
            s_repeat_ = s_repeat.clone()
            indsa = (s_repeat_floor == self.t) & inds
            assert indsa.nonzero().size()[0] == size, ('Not good number of bins')
            zeros = torch.zeros((1, indsa.size()[1])).byte()
            if self.cuda:
                zeros = zeros.cuda()
            indsb = torch.cat((zeros, indsa))[:self.tsize, :]
            s_repeat_[~(indsb|indsa)] = 0
            s_repeat_[indsa] = (s_repeat_ - Variable(self.t).double())[indsa] / self.step
            s_repeat_[indsb] =  (-s_repeat_ + Variable(self.t).double())[indsb] / self.step

            return s_repeat_.sum(1) / size
        
        features, classes = features.double(), classes.double()
        classes_size = classes.size()[0]
        classes_eq = (classes.repeat(classes_size, 1)  == classes.view(-1, 1).repeat(1, classes_size)).data
        dists = torch.mm(features, features.transpose(0, 1))
        s_inds = torch.triu(torch.ones(classes_eq.size()), 1).byte()
        if self.cuda:
            s_inds= s_inds.cuda()
        pos_inds = classes_eq[s_inds].repeat(self.tsize, 1)
        neg_inds = ~classes_eq[s_inds].repeat(self.tsize, 1)
        pos_size = classes_eq[s_inds].sum().item()
        neg_size = (~classes_eq[s_inds]).sum().item()
        s = dists[s_inds].view(1, -1)
        s_repeat = s.repeat(self.tsize, 1)
        s_repeat_floor = (torch.floor(s_repeat.data / self.step) * self.step).float()
        
        histogram_pos = histogram(pos_inds, pos_size)
        assert_almost_equal(histogram_pos.sum().item(), 1, decimal=2, 
                            err_msg='Not good positive histogram', verbose=True)
        histogram_neg = histogram(neg_inds, neg_size)
        assert_almost_equal(histogram_neg.sum().item(), 1, decimal=2, 
                            err_msg='Not good negative histogram', verbose=True)
        histogram_pos_repeat = histogram_pos.view(-1, 1).repeat(1, histogram_pos.size()[0])
        histogram_pos_inds = torch.tril(torch.ones(histogram_pos_repeat.size()), -1).byte()
        if self.cuda:
            histogram_pos_inds = histogram_pos_inds.cuda()
        histogram_pos_repeat[histogram_pos_inds] = 0
        histogram_pos_cdf = histogram_pos_repeat.sum(0)
        loss = torch.sum(histogram_neg * histogram_pos_cdf)
        
        return loss
   
